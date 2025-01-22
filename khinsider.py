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

KHINSIDER_ALBUM_URL_REGEX = (
    r'https:\/\/downloads\.khinsider\.com\/'
    r'game-soundtracks\/album\/([\w-]+)\/?([\w%.]+)?'
)
KHINSIDER_BASE_URL = 'https://downloads.khinsider.com'

DOWNLOADS_PATH = Path('downloads')

THREAD_COUNT = 4


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


class KhinsiderDownloader:
    def __init__(self):
        self.worker_limit = THREAD_COUNT
        self.executor = None
        self.tasks = []

    def download_track(self, url: str, album_slug: str):
        track_filename = unquote(unquote(url.rsplit('/', 1)[-1]))
        logging.info(f'Downloading track {track_filename} from {album_slug}')

        response = get_http(url)

        soup = bs(response.text, 'lxml')
        audio_url = soup.select_one('audio')['src']

        audio_response = get_http(audio_url)

        file_path = DOWNLOADS_PATH / album_slug / track_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open('wb') as f:
            f.write(audio_response.content)

    def download_from_link(self, url: str) -> None:
        match = re.match(KHINSIDER_ALBUM_URL_REGEX, url)

        if not match:
            logging.error(f'Invalid link: {url}')
            return

        album_slug = match[1]

        if match[2]:
            self.download_track(url, album_slug)
            return

        # TODO: Collect tracks separately from futures
        logging.info(f'Collecting tracks from {url}')
        response = get_http(url)

        soup = bs(response.text, 'lxml')
        songlist_rows = soup.select_one('#songlist').select('tr')

        for i, row in enumerate(songlist_rows):
            anchor = row.select_one('td a')
            if not anchor:
                continue

            track_url = KHINSIDER_BASE_URL + anchor['href']
            logging.info(f'[{i}] Downloading {track_url}')
            self.submit_download(track_url)

        logging.info(f'All tracks submitted: {album_slug}')

    def __enter__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.worker_limit)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.executor.shutdown()
        self.executor = None

    def submit_download(self, link: str):
        if not self.executor:
            raise RuntimeError('Executor is not running')

        logging.info(f'{link} submitted for download!')
        self.tasks.append(self.executor.submit(self.download_from_link, link))

    def download(self, links: str):
        for link in links:
            self.submit_download(link)

        wait(self.tasks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--file',
        '-f',
        help='File containing links to be downloaded',
        required=True,
    )
    args = parser.parse_args()

    links = read_links_from_file(args.file)

    with KhinsiderDownloader() as downloader:
        downloader.download(links)


if __name__ == '__main__':
    main()
