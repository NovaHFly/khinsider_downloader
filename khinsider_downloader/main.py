from pathlib import Path

import click
import progressbar as prgbar
import requests as req
from bs4 import BeautifulSoup as bs

ALBUM_BASE_URL = 'https://downloads.khinsider.com/game-soundtracks/album/'
URL_DECODE_API = 'https://www.urldecode.org'

DOWNLOAD_PATH = Path('./Download')


def check_url(url: str) -> bool:
    """Check if url is a valid khinsider album url."""
    return url.startswith(ALBUM_BASE_URL)


def make_album_dir(album_url: str) -> Path:
    """Create and return album download dir path."""
    dir_name = album_url.removeprefix(ALBUM_BASE_URL)
    album_dir_path = DOWNLOAD_PATH / dir_name
    album_dir_path.mkdir(exist_ok=True, parents=True)
    return album_dir_path


def get_audio_url_from(detail_path: str) -> str:
    """Get audio file url from song detail path."""
    item_detail_url = 'https://downloads.khinsider.com' + detail_path

    response = req.get(item_detail_url)
    soup = bs(response.text, 'lxml')

    audio_url = soup.select_one('audio').attrs['src']
    return audio_url


def url_decode_string(string: str) -> str:
    """Decode url-encoded character in the string."""
    params = {'text': string, 'mode': 'decode'}
    decoded_string = (
        bs(req.get(URL_DECODE_API, params=params).text, 'lxml')
        .select_one('input')
        .attrs['value']
    )
    return decoded_string


def create_progress_bar(total_length: int, caption: str) -> prgbar.ProgressBar:
    """Create a progress bar to track file download."""
    return prgbar.ProgressBar(
        maxval=total_length,
        widgets=[
            caption,
            prgbar.Bar(left='[', marker='=', right=']'),
            prgbar.SimpleProgress(),
        ],
    ).start()


@click.command()
@click.argument('album_url')
def main(album_url: str) -> None:
    """Download all audio files from album_url."""
    if not check_url(album_url):
        print(f'Invalid link: {album_url}!')
        return

    album_dir_path = make_album_dir(album_url)

    response = req.get(album_url)

    text = response.text

    if any(line in text for line in ('No such album', 'Click here')):
        print('Album not found or invalid link!')
        return

    soup = bs(text, 'lxml')
    songlist_items = soup.select_one('#songlist').select('tr')

    for item in songlist_items:
        if not item.select('td'):
            continue

        tag_anchor = item.select_one('a')
        if not tag_anchor:
            continue

        item_detail_path = tag_anchor.attrs['href']
        audio_url = get_audio_url_from(item_detail_path)

        file_name = audio_url.rsplit('/', maxsplit=1)[-1]
        file_name = url_decode_string(file_name)

        stream = req.get(audio_url, stream=True)
        audio_total_length = int(stream.headers.get('content-length'))

        bar = create_progress_bar(audio_total_length, file_name)

        audio_current_length = 0
        with (album_dir_path / file_name).open('wb') as f:
            for data in stream.iter_content(chunk_size=2048):
                f.write(data)
                audio_current_length += len(data)
                bar.update(audio_current_length)
            print(file_name + ' : Download completed'.ljust(128))

    print('All files downloaded!')
