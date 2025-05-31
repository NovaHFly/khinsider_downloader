import re
from functools import cache
from logging import getLogger

import httpx
from bs4 import BeautifulSoup as bs, Tag
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .constants import (
    ALBUM_INFO_BASE_URL,
    KHINSIDER_BASE_URL,
    KHINSIDER_URL_REGEX,
)
from .decorators import log_errors
from .exceptions import InvalidUrl, ItemDoesNotExist
from .models import Album, AudioTrack

logger = getLogger('khinsider_api')


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@cache
@log_errors
def get_album_data(album_url: str) -> Album:
    def parse_album_year(album_info_txt: str) -> str:
        if match := re.search(r'Year: (\d{4})', album_info_txt):
            return match[1]
        return None

    def parse_album_type(album_info_tag: Tag) -> str:
        if type_tag := album_info_tag.select_one('p[align=left] b a'):
            return type_tag.text
        return None

    if not (match := re.match(KHINSIDER_URL_REGEX, album_url)):
        err_msg = f'Invalid album link: {album_url}'
        raise InvalidUrl(err_msg)

    album_page_res = httpx.get(album_url).raise_for_status()
    if 'No such album' in album_page_res.text:
        raise ItemDoesNotExist(f'Album does not exist: {album_url}')

    soup = bs(album_page_res.text, 'lxml')

    album_info_url = ALBUM_INFO_BASE_URL.format(album_slug=match[1])
    album_info = httpx.get(album_info_url).raise_for_status().text

    track_urls = [
        KHINSIDER_BASE_URL + anchor['href']
        for row in soup.select('#songlist tr')
        if (anchor := row.select_one('td a'))
    ]

    album = Album(
        name=soup.select_one('h2').text,
        slug=match[1],
        thumbnail_urls=[
            img.attrs['src'] for img in soup.select('.albumImage img')
        ],
        year=parse_album_year(album_info),
        type=parse_album_type(soup.select_one('p[align=left]')),
        track_urls=track_urls,
    )
    logger.info(f'Scraped album: {album}')
    return album


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@cache
@log_errors
def get_track_data(url: str) -> AudioTrack:
    """Get track data from url."""
    match = re.match(KHINSIDER_URL_REGEX, url)

    if not match or not match[2]:
        err_msg = f'Invalid track url: {url}'
        raise InvalidUrl(err_msg)

    try:
        response = httpx.get(url).raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ItemDoesNotExist(f'Track does not exist: {url}')
        raise

    soup = bs(response.text, 'lxml')
    audio_url = soup.select_one('audio')['src']

    album = get_album_data(url.rsplit('/', maxsplit=1)[0])

    track = AudioTrack(album=album, page_url=url, mp3_url=audio_url)
    logger.info(track)

    return track
