import logging
import re
from concurrent.futures import as_completed, Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup as bs
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .constants import (
    ALBUM_INFO_BASE_URL,
    DEFAULT_THREAD_COUNT,
    DOWNLOADS_PATH,
    KHINSIDER_BASE_URL,
    KHINSIDER_URL_REGEX,
)
from .decorators import log_errors, log_time
from .exceptions import InvalidUrl, ItemDoesNotExist

logger = logging.getLogger('khinsider')


@dataclass
class AudioTrack:
    name: str = field(init=False)
    filename: str = field(init=False)

    album: 'Album' = field(repr=False)
    khinsider_page_url: str = field(repr=False)
    mp3_url: str | None = field(repr=False, default=None)

    size: int = field(repr=False, default=0)

    def __str__(self) -> str:
        return f'{self.album.slug} - {self.filename}'

    @log_errors
    def __post_init__(self) -> None:
        if not (
            match := re.match(
                KHINSIDER_URL_REGEX,
                self.khinsider_page_url,
            )
        ):
            raise InvalidUrl(
                f'Invalid khinsider url: {self.khinsider_page_url}'
            )
        self.filename = unquote(unquote(match[2]))
        self.name = str(self)


@dataclass
class Album:
    name: str
    slug: str

    thumbnail_urls: list[str]

    year: str
    type: str
    track_count: int = field(init=False)

    track_urls: list[str] = field(
        repr=False,
        compare=False,
        hash=False,
        default_factory=list,
    )
    tracks: list[AudioTrack] = field(
        init=False,
        repr=False,
        default_factory=list,
    )

    def __post_init__(self) -> None:
        for track_url in self.track_urls:
            self.tracks.append(
                AudioTrack(
                    album=self,
                    khinsider_page_url=track_url,
                )
            )
        self.track_count = len(self.tracks)


def separate_album_and_track_urls(
    urls: list[str],
) -> tuple[list[str], list[str]]:
    """Separate album and track urls into two lists."""
    album_urls = []
    track_urls = []

    for url in urls:
        if not (match := re.match(KHINSIDER_URL_REGEX, url)):
            logger.error(f'Invalid khinsider url: {url}')
            continue

        if match[2]:
            track_urls.append(url)
            continue

        album_urls.append(url)

    return album_urls, track_urls


@cache
@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@log_errors
def get_album_data(album_url: str, collect_tracks: bool = True) -> Album:
    if not (match := re.match(KHINSIDER_URL_REGEX, album_url)):
        err_msg = f'Invalid album link: {album_url}'
        raise InvalidUrl(err_msg)

    album_page_res = httpx.get(album_url).raise_for_status()
    if 'No such album' in album_page_res.text:
        raise ItemDoesNotExist(f'Album does not exist: {album_url}')

    soup = bs(album_page_res.text, 'lxml')

    album_info_url = ALBUM_INFO_BASE_URL.format(album_slug=match[1])
    album_info = httpx.get(album_info_url).raise_for_status().text

    track_urls = []
    if collect_tracks:
        track_urls = [
            KHINSIDER_BASE_URL + anchor['href']
            for row in soup.select('#songlist tr')
            if (anchor := row.select_one('td a'))
        ]

    return Album(
        name=soup.select_one('h2').text,
        slug=match[1],
        thumbnail_urls=[
            img.attrs['src'] for img in soup.select('.albumImage img')
        ],
        year=re.search(r'Year: (\d{4})', album_info).group(1),
        type=soup.select('p[align=left] a')[-1].text,
        track_urls=track_urls,
    )


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@log_errors
def get_track_data(url: str, fetch_size: bool = True) -> AudioTrack:
    """Get track data from url."""
    match = re.match(KHINSIDER_URL_REGEX, url)

    if not match:
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

    track_size = (
        int(httpx.head(audio_url).raise_for_status().headers['content-length'])
        if fetch_size
        else 0
    )

    album = get_album_data(
        url.rsplit('/', maxsplit=1)[0],
        collect_tracks=False,
    )

    track = AudioTrack(
        album=album,
        khinsider_page_url=url,
        mp3_url=audio_url,
        size=track_size,
    )

    logger.info(f'Scraped track {track} from {url}')

    return track


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@log_errors
def download_track_file(track: AudioTrack) -> Path:
    """Download track file."""
    response = httpx.get(track.mp3_url).raise_for_status()

    file_path = DOWNLOADS_PATH / track.album.slug / track.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if not track.size:
        track.size = int(response.headers['content-length'])

    with file_path.open('wb') as f:
        f.write(response.content)

    logger.info(f'Downloaded track {track} to {file_path}')

    return file_path


def fetch_and_download_track(url: str) -> tuple[AudioTrack, Path]:
    """Fetch track data and download it."""
    track = get_track_data(url, fetch_size=False)
    return track, download_track_file(track)


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(5),
)
@log_errors
def get_track_urls_from_album(album_url: str) -> list[str]:
    """Get track urls from album page."""
    response = httpx.get(album_url).raise_for_status()

    soup = bs(response.text, 'lxml')
    songlist_rows = soup.select('#songlist tr')

    return [
        KHINSIDER_BASE_URL + anchor['href']
        for row in songlist_rows
        if (anchor := row.select_one('td a'))
    ]


@log_time
def download_tracks(
    *urls: str,
    thread_count: int = DEFAULT_THREAD_COUNT,
) -> list[Future[tuple[AudioTrack, Path]]]:
    """Download all tracks from khinsider urls.

    If provided url is album url, scrape all track urls from it.
    """
    album_urls, track_urls = separate_album_and_track_urls(urls)

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        download_tasks = [
            executor.submit(fetch_and_download_track, url)
            for url in track_urls
        ]

        album_scrape_tasks = [
            executor.submit(get_track_urls_from_album, url)
            for url in album_urls
        ]
        for scrape_task in as_completed(album_scrape_tasks):
            download_tasks.extend(
                executor.submit(fetch_and_download_track, url)
                for url in scrape_task.result()
            )

    return download_tasks
