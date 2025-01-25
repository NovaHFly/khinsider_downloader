import argparse
import logging
import re
from concurrent.futures import Future, ThreadPoolExecutor, wait
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

    If the decorated function raises an exception,
    it will be logged and re-raised.
    Decorator can be used with or without arguments.

    Args:
        func (Callable[P, T], optional): The function to decorate.
            Defaults to None.
        expected_exceptions (ExceptionGroup, optional): The exceptions to log.
            Defaults to Exception.

    Returns:
        Callable[P, T] | Decorator:
        The decorated function or the decorator.
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


httpx.request = retry(stop=stop_after_attempt(5))(
    log_errors(expected_exceptions=httpx.HTTPError)(httpx.request)
)


class KhinsiderDownloader:
    def __init__(self, *, thread_limit: int = THREAD_COUNT) -> None:
        self.thread_limit = thread_limit
        self._executor = None
        self._tasks = []

    def download_track(self, url: str) -> int:
        match = re.match(KHINSIDER_URL_REGEX, url)

        if not match:
            err_msg = f'Invalid track link: {url}'
            logging.error(err_msg)
            raise ValueError(err_msg)

        album_slug = match[1]
        track_filename = unquote(unquote(match[2]))
        logging.info(f'Downloading track {track_filename} from {album_slug}')

        response = httpx.request('GET', url)

        soup = bs(response.text, 'lxml')
        audio_url = soup.select_one('audio')['src']

        audio_response = get_http(audio_url)

        file_path = DOWNLOADS_PATH / album_slug / track_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open('wb') as f:
            f.write(audio_response.content)

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

    links_from_file = (
        args.URLS if args.URLS else Path(args.file).read_text().splitlines()
    )
    album_links = []
    track_links = []

    for link in links_from_file:
        if not (match := re.match(KHINSIDER_URL_REGEX, link)):
            logging.error(f'Invalid khinsider link: {link}')
            continue

        if match[2]:
            track_links.append(link)
            continue

        album_links.append(link)

    with KhinsiderDownloader(thread_limit=args.threads) as downloader:
        album_scrape_tasks = [
            downloader.submit_task(
                downloader.scrape_track_urls_from_album, link
            )
            for link in album_links
        ]
        wait(album_scrape_tasks)
        for scrape_task in album_scrape_tasks:
            track_links.extend(scrape_task.result())

        download_tasks = [
            downloader.submit_task(downloader.download_track, link)
            for link in track_links
        ]

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
