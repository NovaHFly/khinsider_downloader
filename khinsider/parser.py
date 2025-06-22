import logging
import re

from bs4 import BeautifulSoup, Tag

from .constants import KHINSIDER_BASE_URL
from .util import parse_khinsider_url

logger = logging.getLogger('khinsider-parser')


def parse_track_data(html_text: str) -> dict:
    """Parse track data from html."""
    match = re.search(r'<audio.+src="(.+)"', html_text)

    logger.debug(f'parse_track_data:{match = }')

    if not match:
        logger.warning('Track data not found in html')
        return {}

    return {'mp3_url': match[1]}


def parse_album_data(html_text: str) -> dict:
    """Parse album data from html."""
    soup = BeautifulSoup(html_text, 'lxml')

    # * Title
    title_tag = soup.select_one('h2')
    if title_tag := soup.select_one('h2'):
        album_title = title_tag.text
    else:
        logger.warning('Album title not found in html')
        album_title = None

    # * Art
    album_art: list[str] = [
        anchor.attrs['href'] for anchor in soup.select('.albumImage a')
    ]
    if not album_art:
        logger.warning('Album art not found in html')

    # * Year
    if match := re.search(r'Year: <b.(\d{4})</b>', html_text):
        album_year: str | None = match[1]
    else:
        logger.warning('Album year not found in html')
        album_year = None

    # * Type
    if tag := soup.select_one('p[align=left] b a'):
        album_type = tag.text
    else:
        logger.warning('Album type not found in html')
        album_type = None

    # * Track page urls
    track_urls: list[str] = [
        KHINSIDER_BASE_URL + anchor.attrs['href']
        for row in soup.select('#songlist tr')
        if (anchor := row.select_one('td a'))
    ]
    if not track_urls:
        logger.warning('Album track urls not found in html')

    return {
        'name': album_title,
        'thumbnail_urls': album_art,
        'year': album_year,
        'type': album_type,
        'track_urls': track_urls,
    }


def parse_publisher_data(html_text: str) -> dict:
    """Parse publisher data from html."""
    match = re.search(r'Published by:.+<a href=".+/(.+)">(.+)</a>', html_text)
    logger.debug(f'parse_publisher_data:{match = }')

    if not match:
        logger.warning('Publisher data not found in html')
        return {}

    return {
        'name': match[2],
        'slug': match[1],
    }


def parse_search_page(html_text: str) -> list[dict]:
    """Parse search results."""

    def _parse_table_row(row_tag: Tag) -> dict:
        col_tags = row_tag.select('td')[1:]

        if not col_tags or len(col_tags) < 4:
            logger.warning('Unknown row markup')
            return {}

        if not (name_anchor := col_tags[0].select_one('a')):
            logger.warning('No <a> tag found in search table row tag')
            return {}

        album_name = name_anchor.text

        album_slug = parse_khinsider_url(
            KHINSIDER_BASE_URL + name_anchor.attrs['href']
        )[0]

        album_type = col_tags[2].text.strip() or None
        album_year = col_tags[3].text.strip() or None

        return {
            'name': album_name,
            'type': album_type,
            'year': album_year,
            'slug': album_slug,
        }

    soup = BeautifulSoup(html_text, 'lxml')

    if not (result_tags := soup.select('table.albumList tr')[1:]):
        logger.warning(
            'Unknown search table format or search results not found in html'
        )
        return []

    return [
        parsed_row
        for tag in result_tags
        if (parsed_row := _parse_table_row(tag))
    ]
