from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from logging import getLogger
from pathlib import Path

import cloudscraper

from .constants import (
    DOWNLOADS_PATH,
    KHINSIDER_BASE_URL,
    MAX_CONCURRENT_REQUESTS,
)
from .decorators import log_errors, retry_if_timeout
from .enums import AlbumTypes
from .models import (
    Album,
    AlbumShort,
    AudioTrack,
    Publisher,
)
from .parser import (
    parse_album_data,
    parse_publisher_data,
    parse_search_page,
    parse_track_data,
)
from .search import QueryBuilder
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


@retry_if_timeout
@cache
@log_errors(logger=logger)
def get_album(
    album_slug: str,
) -> Album:
    url = f'{KHINSIDER_BASE_URL}/game-soundtracks/album/{album_slug}'

    res = scraper.get(url)
    khinsider_object_exists(res)

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


@retry_if_timeout
@cache
@log_errors(logger=logger)
def get_track(
    album_slug: str,
    track_name: str,
) -> AudioTrack:
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


def fetch_tracks(*track_page_urls: str) -> Iterator[AudioTrack]:
    """Fetch track data from multiple urls."""
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
        tasks = [
            executor.submit(get_track, *parse_khinsider_url(url))
            for url in track_page_urls
        ]
        return (task.result() for task in tasks if not task.exception())


@retry_if_timeout
@cache
@log_errors(logger=logger)
def search_albums(
    query: str, album_type: AlbumTypes = AlbumTypes.EMPTY
) -> list[AlbumShort]:
    full_query = QueryBuilder().search_for(query).build()
    url = f'{KHINSIDER_BASE_URL}/search?{full_query}'

    res = scraper.get(url)

    return [
        AlbumShort(**search_result)
        for search_result in parse_search_page(res.text)
    ]


@retry_if_timeout
@cache
@log_errors(logger=logger)
def get_publisher_albums(publisher_slug: str) -> list[AlbumShort]:
    url = f'{KHINSIDER_BASE_URL}/game-soundtracks/publisher/{publisher_slug}'

    res = scraper.get(url)

    return [
        AlbumShort(**search_result)
        for search_result in parse_search_page(res.text)
    ]


def download_many(
    *urls: str,
    thread_count: int = MAX_CONCURRENT_REQUESTS,
    download_path: Path = DOWNLOADS_PATH,
) -> Iterator[Path | None]:
    """Download all tracks from khinsider urls.

    If provided url is album url, download all tracks from it.
    """
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        for url in urls:
            yield from _download(url, executor, download_path)


def _download(
    url: str,
    download_path: Path,
    executor: ThreadPoolExecutor = None,
) -> Iterator[Path]:
    extracted = parse_khinsider_url(url)

    dl_path = (download_path or DOWNLOADS_PATH).absolute()
    dl_path.mkdir(parents=True, exist_ok=True)

    if extracted[1]:
        yield _fetch_and_download_track(*extracted, path=dl_path)
        return

    album = get_album(extracted[1])

    if not executor:
        yield from (
            _fetch_and_download_track(*parse_khinsider_url(url), path=dl_path)
            for url in album.track_urls
        )
        return

    download_tasks = [
        executor.submit(
            _fetch_and_download_track,
            *parse_khinsider_url(url),
            dl_path,
        )
        for url in album.track_urls
    ]
    yield from (
        task.result() for task in download_tasks if not task.exception()
    )


def _fetch_and_download_track(
    album_slug: str,
    track_name: str,
    path: Path = DOWNLOADS_PATH,
) -> Path:
    """Fetch track data and download it."""
    track = get_track(album_slug, track_name)
    return download_track_file(track, path)


@retry_if_timeout
@log_errors(logger=logger)
def download_track_file(
    track: AudioTrack,
    path: Path = DOWNLOADS_PATH,
) -> Path:
    """Download track file."""
    response = scraper.get(track.mp3_url).raise_for_status()

    file_path = path / track.album.slug / track.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open('wb') as f:
        f.write(response.content)

    logger.info(f'Downloaded track {track} to {file_path}')

    return file_path
