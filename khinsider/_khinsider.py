import logging
import re
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path

import httpx
from bs4 import BeautifulSoup as bs, Tag
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .constants import (
    ALBUM_INFO_BASE_URL,
    DEFAULT_THREAD_COUNT,
    DOWNLOADS_PATH,
    KHINSIDER_BASE_URL,
    KHINSIDER_URL_REGEX,
)
from .decorators import log_errors
from .exceptions import InvalidUrl, ItemDoesNotExist
from .models import Album, AudioTrack

logger = logging.getLogger('khinsider')


class Downloader(ThreadPoolExecutor):
    def download(
        self,
        url: str,
        download_path: Path = DOWNLOADS_PATH,
    ) -> Iterator[Path]:
        if not (match := re.match(KHINSIDER_URL_REGEX, url)):
            raise InvalidUrl(f'Not a valid khinsider url: {url}')

        dl_path = (download_path or DOWNLOADS_PATH).absolute()
        dl_path.mkdir(parents=True, exist_ok=True)

        if match[2]:
            yield fetch_and_download_track(url, path=dl_path)
            return

        album = get_album_data(url)
        download_tasks = [
            self.submit(fetch_and_download_track, url, dl_path)
            for url in album.track_urls
        ]
        yield from (
            task.result() for task in download_tasks if not task.exception()
        )

    def fetch_tracks(
        self,
        track_page_urls: Sequence[str],
    ) -> Iterator[AudioTrack]:
        tasks = [self.submit(get_track_data, url) for url in track_page_urls]
        return (task.result() for task in tasks if not task.exception())


def gather_track_urls(urls: list[str]) -> Iterator[str]:
    """Gather all track urls from khinsider urls.

    If provided url is album url, scrape and yield all track urls
    from its page.
    """
    for url in urls:
        if not (match := re.match(KHINSIDER_URL_REGEX, url)):
            logger.error(f'Invalid khinsider url: {url}')
            continue

        if match[2]:
            yield url
            continue

        yield from get_album_data(url).track_urls


@cache
@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@log_errors
def get_album_data(album_url: str) -> Album:
    def parse_album_year(album_info_txt: str) -> str:
        if match := re.search(r'Year: (\d{4})', album_info):
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


@cache
@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
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


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@log_errors
def download_track_file(
    track: AudioTrack, path: Path = DOWNLOADS_PATH
) -> Path:
    """Download track file."""
    response = httpx.get(track.mp3_url).raise_for_status()

    file_path = path / track.album.slug / track.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if not track.size:
        track.size = int(response.headers['content-length'])

    with file_path.open('wb') as f:
        f.write(response.content)

    logger.info(f'Downloaded track {track} to {file_path}')

    return file_path


def fetch_and_download_track(url: str, path: Path = DOWNLOADS_PATH) -> Path:
    """Fetch track data and download it."""
    track = get_track_data(url)
    return download_track_file(track, path)


def download_many(
    *urls: str,
    thread_count: int = DEFAULT_THREAD_COUNT,
    download_path: Path = DOWNLOADS_PATH,
) -> Iterator[Path | None]:
    """Download all tracks from khinsider urls.

    If provided url is album url, download all tracks from it.
    """
    with Downloader(max_workers=thread_count) as downloader:
        for url in urls:
            yield from downloader.download(url, download_path=download_path)


def download(
    url: str,
    thread_count: int = DEFAULT_THREAD_COUNT,
    download_path: Path = None,
) -> Iterator[Path]:
    with Downloader(max_workers=thread_count) as downloader:
        yield from downloader.download(url, download_path)
