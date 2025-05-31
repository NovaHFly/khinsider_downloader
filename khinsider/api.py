from collections.abc import Callable
from functools import cache
from logging import getLogger

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .constants import (
    KHINSIDER_BASE_URL,
)
from .decorators import log_errors
from .exceptions import InvalidUrl, ItemDoesNotExist
from .models import Album, AudioTrack
from .parser import parse_album_page, parse_track_page

logger = getLogger('khinsider_api')

KHINSIDER_OBJECT_BASE_URL = f'{KHINSIDER_BASE_URL}/game-soundtracks'

# TODO: All validators must return same exception type


def url_is_khinsider_object(response: httpx.Response) -> None:
    url = str(response.url)
    if not url.startswith(KHINSIDER_OBJECT_BASE_URL):
        raise InvalidUrl(f'Invalid khinsider object url: {url}!')


def khinsider_object_exists(response: httpx.Response) -> None:
    url = str(response.url)
    if 'Ooops!' in response.text:
        object_url = url.removeprefix(KHINSIDER_OBJECT_BASE_URL)
        raise ItemDoesNotExist(
            f'Requested object does not exist: {object_url}!'
        )


def url_is_khinsider_album(response: httpx.Response) -> None:
    url = response.url
    if len(url.raw_path.split(b'/')) != 4:
        raise InvalidUrl('Url does not lead to khinsider album page!')


def url_is_khinsider_track(response: httpx.Response) -> None:
    url = response.url
    if len(url.raw_path.split(b'/')) != 5:
        raise InvalidUrl('Url does not lead to khinsider track page!')


@log_errors(logger=logger)
def get_object_response(
    url: str, validators: list[Callable[[httpx.Response], None]] = None
) -> httpx.Response:
    if not validators:
        validators = []

    res = httpx.get(url)

    for validator in validators:
        validator(res)

    return res


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@cache
@log_errors(logger=logger)
def get_album(album_url: str) -> Album:
    album_page_res = get_object_response(
        album_url,
        validators=[
            url_is_khinsider_object,
            khinsider_object_exists,
            url_is_khinsider_album,
        ],
    )

    album_slug = album_url.rsplit('/', maxsplit=1)[-1]

    album_data = parse_album_page(album_page_res.text)
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
def get_track(track_url: str) -> AudioTrack:
    """Get track data from url."""
    track_response = get_object_response(
        track_url,
        validators=[
            url_is_khinsider_object,
            khinsider_object_exists,
            url_is_khinsider_track,
        ],
    )
    album = get_album(track_url.rsplit('/', maxsplit=1)[0])

    track_data = parse_track_page(track_response.text)
    track_data |= {
        'page_url': track_url,
        'album': album,
    }

    track = AudioTrack(**track_data)
    logger.info(track)

    return track
