import argparse
import logging
import re
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
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


def construct_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--file',
        '-f',
        help='File containing album or track urls',
        required=True,
    )
    return parser
@retry(stop=stop_after_attempt(5))
def get_http(url: str) -> httpx.Response:
    try:
        return httpx.get(url).raise_for_status()
    except httpx.HTTPError as e:
        logging.error(e)
        raise


def read_links_from_file(file_path: str) -> list:
    with open(file_path, 'r') as f:
        return [line.strip() for line in f.readlines()]


def scrape_album_track_urls(url: str) -> list[str]:
    response = get_http(url)

    soup = bs(response.text, 'lxml')
    songlist_rows = soup.select_one('#songlist').select('tr')

    return [
        KHINSIDER_BASE_URL + anchor['href']
        for row in songlist_rows
        if (anchor := row.select_one('td a'))
    ]


class KhinsiderDownloader:
    def __init__(self):
        self.worker_limit = THREAD_COUNT
        self.executor = None
        self.tasks = []

    def download_track(self, url: str):
        match = re.match(KHINSIDER_URL_REGEX, url)

        if not match:
            logging.error(f'Invalid track link: {url}')
            return

        album_slug = match[1]
        track_filename = unquote(unquote(match[2]))
        logging.info(f'Downloading track {track_filename} from {album_slug}')

        response = get_http(url)

        soup = bs(response.text, 'lxml')
        audio_url = soup.select_one('audio')['src']

        audio_response = get_http(audio_url)

        file_path = DOWNLOADS_PATH / album_slug / track_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open('wb') as f:
            f.write(audio_response.content)

    def __enter__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.worker_limit)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        wait(self.tasks)
        self.executor.shutdown()
        self.executor = None

    def submit_download(self, link: str):
        if not self.executor:
            raise RuntimeError('Executor is not running')

        logging.info(f'{link} submitted for download!')
        self.tasks.append(self.executor.submit(self.download_track, link))


def main() -> None:
    parser = construct_argparser()
    args = parser.parse_args()

    links_from_file = read_links_from_file(args.file)
    track_links = []

    for link in links_from_file:
        if not (match := re.match(KHINSIDER_URL_REGEX, link)):
            logging.error(f'Invalid khinsider link: {link}')
            continue

        if match[2]:
            track_links.append(link)
            continue

        track_links.extend(scrape_album_track_urls(link))

    with KhinsiderDownloader() as downloader:
        for link in track_links:
            downloader.submit_download(link)


if __name__ == '__main__':
    main()
