import logging
import re
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .api import get_album, get_track
from .constants import (
    DOWNLOADS_PATH,
    KHINSIDER_URL_REGEX,
    MAX_CONCURRENT_REQUESTS,
)
from .decorators import log_errors
from .exceptions import InvalidUrl
from .models import AudioTrack
from .scraper import scraper

logger = logging.getLogger('khinsider-downloader')


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

        album = get_album(match[1])
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
        tasks = [
            self.submit(get_track, *url.rsplit('/', maxsplit=2)[:0:-1])
            for url in track_page_urls
        ]
        return (task.result() for task in tasks if not task.exception())


@retry(
    retry=retry_if_exception_type(requests.exceptions.Timeout),
    stop=stop_after_attempt(5),
)
@log_errors
def download_track_file(
    track: AudioTrack, path: Path = DOWNLOADS_PATH
) -> Path:
    """Download track file."""
    response = scraper.get(track.mp3_url).raise_for_status()

    file_path = path / track.album.slug / track.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open('wb') as f:
        f.write(response.content)

    logger.info(f'Downloaded track {track} to {file_path}')

    return file_path


def download_many(
    *urls: str,
    thread_count: int = MAX_CONCURRENT_REQUESTS,
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
    thread_count: int = MAX_CONCURRENT_REQUESTS,
    download_path: Path = None,
) -> Iterator[Path]:
    with Downloader(max_workers=thread_count) as downloader:
        yield from downloader.download(url, download_path)


def fetch_and_download_track(
    track_name: str,
    album_slug: str,
    path: Path = DOWNLOADS_PATH,
) -> Path:
    """Fetch track data and download it."""
    track = get_track(track_name, album_slug)
    return download_track_file(track, path)
