import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger

import cloudscraper
from bs4 import BeautifulSoup, Tag

from ._types import AlbumBaseJson, AlbumPageJson, PublisherJson, TrackJson
from .constants import (
    KHINSIDER_BASE_URL,
    MAX_CONCURRENT_REQUESTS,
)
from .decorators import log_errors, retry_if_timeout
from .exceptions import NoRequestedDataInHtml
from .util import parse_khinsider_url
from .validators import (
    khinsider_object_exists,
)

scraper = cloudscraper.create_scraper(
    interpreter='js2py',
    delay=5,
    max_concurrent_requests=MAX_CONCURRENT_REQUESTS + 1,
    enable_stealth=True,
    stealth_options={
        'min_delay': 2.0,
        'max_delay': 6.0,
        'human_like_delays': True,
        'randomize_headers': True,
        'browser_quirks': True,
    },
    browser='chrome',
)


logger = getLogger('khinsider-scraper')


def fetch_mp3_urls(*track_page_urls: str) -> Iterator[str]:
    """Fetch mp3 file urls for provided track pages.

    :param str *track_page_urls: Track pages from which to extract mp3 urls.
    :return Iterator[str]: Mp3 urls.
    """
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
        tasks = [
            executor.submit(scrape_track_page, url) for url in track_page_urls
        ]
        yield from (
            task.result()['mp3_url'] for task in tasks if not task.exception()
        )


@log_errors(logger=logger)
@retry_if_timeout
def scrape_album_page(album_url: str) -> AlbumPageJson:
    """Fetch album page html and scrape data from it.

    :param str album_url: Album page url from which to fetch html.
    :return AlbumPageJson: Album json object.
    """

    def _parse_album_html() -> AlbumPageJson:
        soup = BeautifulSoup(album_html, 'lxml')

        # * Album name
        title_tag = soup.select_one('h2')
        if not title_tag:
            err_msg = 'Album title not found in html'
            logger.error(err_msg)
            raise NoRequestedDataInHtml(err_msg)
        album_title = title_tag.text

        # * Album year
        album_year: str | None
        if year_match := re.search(r'Year: <b.(\d{4})</b>', album_html):
            album_year = year_match[1]
        else:
            logger.warning('Album year not found in html')
            album_year = None

        # * Album type
        album_type: str | None
        if type_tag := soup.select_one('p[align=left] b a'):
            album_type = type_tag.text
        else:
            logger.warning('Album type not found in html')
            album_type = None

        # * Album art
        album_art: list[str] = [
            anchor.attrs['href'] for anchor in soup.select('.albumImage a')
        ]
        if not album_art:
            logger.warning('Album art not found in html')

        # * Album tracks
        track_urls: list[str] = [
            KHINSIDER_BASE_URL + anchor.attrs['href']
            for anchor in soup.select(
                '#songlist tr td:first-of-type + td + td a'
            )
        ]
        if not track_urls:
            logger.warning('Album track urls not found in html')

        # * Publisher
        publisher_data: PublisherJson | None
        if publisher_match := re.search(
            r'Published by:.+<a href=".+/(.+)">(.+)</a>', album_html
        ):
            publisher_data = {
                'name': publisher_match[2],
                'slug': publisher_match[1],
            }
        else:
            logger.warning('Publisher data not found in html')
            publisher_data = None

        return {
            'title': album_title,
            'year': album_year,
            'type': album_type,
            'album_art': album_art,
            'track_urls': track_urls,
            'slug': album_slug,
            '_publisher': publisher_data,
        }

    album_slug = parse_khinsider_url(album_url)[0]

    response = scraper.get(album_url)
    khinsider_object_exists(response)

    album_html = response.text

    return _parse_album_html()


@log_errors(logger=logger)
@retry_if_timeout
def scrape_track_page(track_url: str) -> TrackJson:
    """Fetch track page html and scrape data from it.

    :param str track_url: Track page from which to fetch html.
    :return TrackJson: Track json object.
    """

    def _parse_track_html() -> TrackJson:
        if not (audio_match := re.search(r'<audio.+src="(.+)', track_html)):
            err_msg = 'Mp3 audio url not found in html'
            logger.error(err_msg)
            raise NoRequestedDataInHtml(err_msg)

        track_mp3_url = audio_match[1]

        return {
            'page_url': track_url,
            'mp3_url': track_mp3_url,
        }

    response = scraper.get(track_url)
    khinsider_object_exists(response)

    track_html = response.text

    return _parse_track_html()


@log_errors(logger=logger)
@retry_if_timeout
def scrape_search_page(search_url: str) -> list[AlbumBaseJson]:
    """Fetch search page html and extract search result data.

    :param str search_url: Search page url from which to fetch html.
    :return list[AlbumBaseJson]: List of shortened album json objects.
    """

    def _parse_table_row(row_tag: Tag) -> AlbumBaseJson | None:
        col_tags = row_tag.select('td')[1:]

        if not col_tags or len(col_tags) < 4:
            logger.warning('Unknown row format')
            return None

        if not (title_anchor := col_tags[0].select_one('a')):
            logger.warning(
                'No anchor tag corresponding to album title found in table row'
            )
            return None

        album_title = title_anchor.text
        album_slug = parse_khinsider_url(
            KHINSIDER_BASE_URL + title_anchor.attrs['href']
        )[0]

        album_type = col_tags[2].text.strip() or None
        album_year = col_tags[3].text.strip() or None

        return {
            'title': album_title,
            'slug': album_slug,
            'type': album_type,
            'year': album_year,
        }

    response = scraper.get(search_url)

    soup = BeautifulSoup(response.text, 'lxml')

    if not (table_rows := soup.select('table.albumList tr')[1:]):
        logger.warning(
            'Unknown search page format or search results not found in html'
        )
        return []

    scraped_results = [
        parsed_row
        for row in table_rows
        if (parsed_row := _parse_table_row(row))
    ]
    if not scraped_results:
        err_msg = 'No search results were parsed from page'
        logger.error(err_msg)
        raise NoRequestedDataInHtml(err_msg)

    return scraped_results
