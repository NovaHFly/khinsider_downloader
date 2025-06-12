from functools import cache
from logging import getLogger

import cloudscraper
import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .constants import KHINSIDER_BASE_URL
from .decorators import log_errors
from .models import (
    Album,
    AlbumShort,
    AudioTrack,
    Publisher,
)
from .parser import (
    parse_album_data,
    parse_album_search_result,
    parse_publisher_data,
    parse_track_data,
)
from .search import QueryBuilder
from .validators import (
    khinsider_object_exists,
)

scraper = cloudscraper.create_scraper(
    interpreter='js2py',
    delay=5,
    enable_stealth=True,
    max_concurrent_requests=2,
    stealth_options={
        'min_delay': 2.0,
        'max_delay': 6.0,
        'human_like_delays': True,
        'randomize_headers': True,
        'browser_quirks': True,
    },
    browser='chrome',
)

logger = getLogger('khinsider_api')


@retry(
    retry=retry_if_exception_type(requests.exceptions.Timeout),
    stop=stop_after_attempt(5),
)
@cache
@log_errors(logger=logger)
def get_album(slug: str) -> Album:
    url = f'{KHINSIDER_BASE_URL}/game-soundtracks/album/{slug}'

    res = scraper.get(url)
    khinsider_object_exists(res)

    album_slug = url.rsplit('/', maxsplit=1)[-1]

    album_data = parse_album_data(res.text)
    album_data |= {'slug': album_slug}

    publisher_data = parse_publisher_data(res.text)
    if not publisher_data:
        publisher = None
    else:
        publisher = Publisher(**publisher_data)

    album_data |= {'publisher': publisher}

    album = Album(**album_data)
    logger.info(album)
    return album


@retry(
    retry=retry_if_exception_type(requests.exceptions.Timeout),
    stop=stop_after_attempt(5),
)
@cache
@log_errors
def get_track(track_name: str, album_slug: str) -> AudioTrack:
    """Get track data from url."""
    url = (
        f'{KHINSIDER_BASE_URL}/game-soundtracks/album/'
        f'{album_slug}/{track_name}'
    )

    res = scraper.get(url)
    khinsider_object_exists(res)

    album = get_album(album_slug)

    track_data = parse_track_data(res.text)
    if not track_data:
        raise ValueError('Page does not contain track audio!')

    track_data |= {
        'page_url': url,
        'album': album,
    }

    track = AudioTrack(**track_data)
    logger.info(track)

    return track


@retry(
    retry=retry_if_exception_type(requests.exceptions.Timeout),
    stop=stop_after_attempt(5),
)
@log_errors
def search_albums(query: str) -> list[AlbumShort]:
    full_query = QueryBuilder().search_for(query).build()

    url = f'{KHINSIDER_BASE_URL}/search?{full_query}'
    res = scraper.get(url)

    soup = BeautifulSoup(res.text, 'lxml')

    if not (result_tags := soup.select('table.albumList tr')):
        return []

    result_tags = result_tags[1:]

    return [
        AlbumShort(**parse_album_search_result(tag)) for tag in result_tags
    ]


# FIXME: Duplicate code with above function
@retry(
    retry=retry_if_exception_type(requests.exceptions.Timeout),
    stop=stop_after_attempt(5),
)
@log_errors
def get_publisher_albums(publisher_slug: str) -> list[AlbumShort]:
    url = f'{KHINSIDER_BASE_URL}/game-soundtracks/publisher/{publisher_slug}'
    res = scraper.get(url)

    soup = BeautifulSoup(res.text, 'lxml')

    if not (result_tags := soup.select('table.albumList tr')):
        return []

    result_tags = result_tags[1:]

    return [
        AlbumShort(**parse_album_search_result(tag)) for tag in result_tags
    ]
