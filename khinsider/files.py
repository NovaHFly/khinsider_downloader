import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from random import randint
from shutil import rmtree

from .api import get_album, get_track
from .constants import DOWNLOADS_PATH, MAX_CONCURRENT_REQUESTS
from .decorators import log_errors, retry_if_timeout
from .models import Track
from .scraper import scraper
from .util import parse_khinsider_url

logger = logging.getLogger('khinsider-files')


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
            yield from _download(url, download_path, executor)


def _download(
    url: str,
    download_path: Path,
    executor: ThreadPoolExecutor | None = None,
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
    track: Track,
    path: Path = DOWNLOADS_PATH,
) -> Path:
    """Download track file."""
    response = scraper.get(track.mp3_url)
    response.raise_for_status()

    file_path = path / track.album.slug / track.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open('wb') as f:
        f.write(response.content)

    logger.info(f'Downloaded track {track} to {file_path}')

    return file_path


@contextmanager
def setup_download(root_path: Path = DOWNLOADS_PATH) -> Iterator[Path]:
    """Setup download path and remove it when done."""
    download_id = randint(1, 999999)
    download_dir = root_path / str(download_id)

    try:
        yield download_dir
    finally:
        rmtree(download_dir, ignore_errors=True)
