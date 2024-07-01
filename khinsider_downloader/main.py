import os
from pathlib import Path

import click
import progressbar as prgbar
import requests as req
from bs4 import BeautifulSoup as bs

ALBUM_BASE_URL = 'https://downloads.khinsider.com/game-soundtracks/album/'

DOWNLOAD_PATH = Path('./Download')


def check_url(url: str) -> bool:
    """Check if url is a valid khinsider album url."""
    return url.startswith(ALBUM_BASE_URL)


@click.command()
@click.argument('album_url')
def main(album_url: str) -> None:
    """Download all audio files from album_url."""
    if not check_url(album_url):
        print(f'Invalid link: {album_url}!')
        return

    dir_name = album_url.removeprefix(ALBUM_BASE_URL)
    album_dir_path = DOWNLOAD_PATH / dir_name
    album_dir_path.mkdir(exist_ok=True, parents=True)

    response = req.get(album_url)
    text = response.text
    if any(line in text for line in ('No such album', 'Click here')):
        print('Album not found or invalid link!')
        return

    soup = bs(text, 'lxml')
    songlist_items = soup.select_one('#songlist').select('tr')

    for child in songlist_items:
        if not child.select('td'):
            continue

        tag_anchor = child.select_one('a')
        if not tag_anchor:
            continue

        link = tag_anchor.attrs['href']
        new_link = 'https://downloads.khinsider.com' + link

        individual_link = req.get(new_link)
        child_page = bs(individual_link.text, 'lxml')
        audio_link = child_page.select_one('audio').attrs['src']

        audio = req.get(audio_link, stream=True)
        file_name = audio_link[audio_link.rfind('/') + 1 :]

        url = 'https://www.urldecode.org'
        params = {'text': file_name, 'mode': 'decode'}
        decoded_name = (
            bs(req.get(url, params=params).text, 'lxml')
            .find('input')
            .attrs['value']
        )

        audio_total_length = int(audio.headers.get('content-length'))

        bar = prgbar.ProgressBar(
            maxval=audio_total_length,
            widgets=[
                decoded_name,  # Статический текст
                prgbar.Bar(left='[', marker='=', right=']'),  # Прогресс
                prgbar.SimpleProgress(),  # Надпись "6 из 10"
            ],
        ).start()

        audio_current_length = 0
        with open(os.path.join(album_dir_path, decoded_name), 'wb') as f:
            for data in audio.iter_content(chunk_size=2048):
                f.write(data)
                audio_current_length += len(data)
                bar.update(audio_current_length)
            print(decoded_name + ' : Download completed' + ' ' * 51)

    print('All files downloaded!')
