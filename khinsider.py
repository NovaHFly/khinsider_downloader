import argparse
import logging
import re
import time
from concurrent.futures import (
    as_completed,
    Future,
    ThreadPoolExecutor,
    wait,
)
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from types import TracebackType
from typing import Callable, ParamSpec, Type, TypeVar
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup as bs
from tenacity import retry, stop_after_attempt

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
)
logging.getLogger().addHandler(logging.StreamHandler())

KHINSIDER_URL_REGEX = (
    r'https:\/\/downloads\.khinsider\.com\/'
    r'game-soundtracks\/album\/([\w-]+)\/?([\w%.-]+)?'
)
KHINSIDER_BASE_URL = 'https://downloads.khinsider.com'

DOWNLOADS_PATH = Path('downloads')

THREAD_COUNT = 6

P = ParamSpec('P')
T = TypeVar('T')

Decorator = Callable[[Callable[P, T]], Callable[P, T]]
ExceptionGroup = tuple[Exception, ...]


@dataclass
class AudioTrack:
    filename: str
    album_slug: str
    url: str
    size: int = 0

    def __str__(self):
        return f'{self.album_slug} - {self.filename}'


def construct_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--file',
        '-f',
        help='File containing album or track urls',
        required=False,
    )
    input_group.add_argument(
        'URLS',
        help='Album or track urls',
        nargs='*',
        default=[],
    )
    parser.add_argument('--threads', '-t', type=int, default=THREAD_COUNT)

    return parser


def log_errors(
    func: Callable[P, T] = None,
    *,
    expected_exceptions: ExceptionGroup = (Exception,),
) -> Callable[P, T] | Decorator:
    """A decorator to log exceptions.

    If the decorated function raises one of expected exceptions,
    it will be logged and re-raised.

    Decorator can be used with or without arguments.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except expected_exceptions as e:
                logging.error(e)
                raise

        return wrapper

    if func:
        return decorator(func)

    return decorator


def log_time(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to log real time elapsed by function."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.info(
            f'{func.__name__} took {end_time - start_time:.2f} seconds'
        )
        return result

    return wrapper


httpx.request = retry(stop=stop_after_attempt(5))(
    log_errors(expected_exceptions=httpx.HTTPError)(httpx.request)
)


class KhinsiderDownloader:
    def __init__(self, *, thread_limit: int = THREAD_COUNT) -> None:
        """Khinsider downloader.

        Args:
            thread_limit (int, optional): Thread limit.
                Defaults to THREAD_COUNT.
        """
        self.thread_limit = thread_limit
        self._executor = None
        self._tasks = []

    def scrape_track_data(self, url: str, get_size: bool = True) -> AudioTrack:
        """Scrape track data from url.

        Args:
            url (str): khinsider track url.
            get_size (bool, optional): Get track size. Defaults to True.

        Returns:
            AudioTrack: Track data.
        """
        match = re.match(KHINSIDER_URL_REGEX, url)

        if not match:
            err_msg = f'Invalid track link: {url}'
            logging.error(err_msg)
            raise ValueError(err_msg)

        album_slug = match[1]
        track_filename = unquote(unquote(match[2]))

        response = httpx.request('GET', url)

        soup = bs(response.text, 'lxml')
        audio_url = soup.select_one('audio')['src']

        track_size = (
            int(httpx.request('HEAD', audio_url).headers['content-length'])
            if get_size
            else 0
        )

        return AudioTrack(track_filename, album_slug, audio_url, track_size)

    def download_track_file(self, track: AudioTrack) -> Path:
        """Download track file.

        Args:
            track (AudioTrack): Track data.

        Returns:
            Path: Downloaded track file path.
        """
        logging.info(f'Downloading track {track}...')

        response = httpx.request('GET', track.url)

        file_path = DOWNLOADS_PATH / track.album_slug / track.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not track.size:
            track.size = int(response.headers['content-length'])

        with file_path.open('wb') as f:
            f.write(response.content)

        return file_path

    def download_track(self, url: str) -> tuple[AudioTrack, Path]:
        """Get track data and download it.

        Args:
            url (str): khinsider track url.

        Returns:
            tuple[AudioTrack, Path]: Track data and downloaded track file path.
        """
        track = self.scrape_track_data(url, get_size=False)
        return track, self.download_track_file(track)

    def scrape_track_urls_from_album(self, url: str) -> list[str]:
        """Scrape track urls from album url.

        Args:
            url (str): khinsider album url.

        Returns:
            list[str]: List of track urls.
        """
        response = httpx.request('GET', url)

        soup = bs(response.text, 'lxml')
        songlist_rows = soup.select_one('#songlist').select('tr')

        return [
            KHINSIDER_BASE_URL + anchor['href']
            for row in songlist_rows
            if (anchor := row.select_one('td a'))
        ]

    def __enter__(self):
        self._executor = ThreadPoolExecutor(max_workers=self.thread_limit)
        return self

    def __exit__(
        self,
        exc_type: Type[Exception],
        exc_value: Exception,
        traceback: TracebackType,
    ) -> None:
        wait(self._tasks)
        self._executor.shutdown()
        self._executor = None
        self._tasks = []

    def submit_task(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> Future[T]:
        if not self._executor:
            raise RuntimeError('Executor is not running')

        task = self._executor.submit(func, *args, **kwargs)
        self._tasks.append(task)
        return task


def main() -> None:
    parser = construct_argparser()
    args = parser.parse_args()

    urls_from_file = (
        args.URLS if args.URLS else Path(args.file).read_text().splitlines()
    )
    album_urls = []
    track_urls = []

    for url in urls_from_file:
        if not (match := re.match(KHINSIDER_URL_REGEX, url)):
            logging.error(f'Invalid khinsider url: {url}')
            continue

        if match[2]:
            track_urls.append(url)
            continue

        album_urls.append(url)

    with KhinsiderDownloader(thread_limit=args.threads) as downloader:
        download_tasks = [
            downloader.submit_task(downloader.download_track, url)
            for url in track_urls
        ]

        album_scrape_tasks = [
            downloader.submit_task(
                downloader.scrape_track_urls_from_album, url
            )
            for url in album_urls
        ]
        for scrape_task in as_completed(album_scrape_tasks):
            download_tasks.extend(
                downloader.submit_task(downloader.download_track, url)
                for url in scrape_task.result()
            )

    download_count = len(download_tasks)
    successful_tasks = [
        task for task in download_tasks if not task.exception()
    ]
    success_count = len(successful_tasks)

    downloaded_bytes = sum(task.result()[0].size for task in successful_tasks)

    logging.info(f'Downloaded {success_count}/{download_count} tracks')
    logging.info(f'Download size: {downloaded_bytes / 1024 / 1024:.2f} MB')


if __name__ == '__main__':
    main()
