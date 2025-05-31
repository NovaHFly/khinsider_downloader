from functools import cache
from logging import getLogger

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .decorators import log_errors
from .models import Album, AudioTrack
from .parser import parse_album_page, parse_track_page
from .validators import (
    khinsider_object_exists,
    url_is_khinsider_album,
    url_is_khinsider_track,
)

logger = getLogger('khinsider_api')


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@cache
@log_errors(logger=logger)
def get_album(url: str) -> Album:
    url_is_khinsider_album(url)

    res = httpx.get(url)
    khinsider_object_exists(res)

    album_slug = url.rsplit('/', maxsplit=1)[-1]

    album_data = parse_album_page(res.text)
    album_data |= {'slug': album_slug}

    album = Album(**album_data)
    logger.info(album)
    return album


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@cache
@log_errors
def get_track(url: str) -> AudioTrack:
    """Get track data from url."""
    url_is_khinsider_track(url)

    res = httpx.get(url)
    khinsider_object_exists(res)

    album = get_album(url.rsplit('/', maxsplit=1)[0])

    track_data = parse_track_page(res.text)
    track_data |= {
        'page_url': url,
        'album': album,
    }

    track = AudioTrack(**track_data)
    logger.info(track)

    return track
