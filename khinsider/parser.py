import re
from typing import Any

from bs4 import BeautifulSoup

from .constants import KHINSIDER_BASE_URL


def parse_track_page(html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text, 'lxml')
    return {'mp3_url': soup.select_one('audio')['src']}


def parse_album_page(html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text, 'lxml')
    return {
        'name': soup.select_one('h2').text,
        'thumbnail_urls': [
            img.attrs['src'] for img in soup.select('.albumImage img')
        ],
        'year': (
            match[1]
            if (match := re.search(r'Year: <b.(\d{4})</b>', html_text))
            else None
        ),
        'type': (
            tag.text if (tag := soup.select_one('p[align=left] a b')) else None
        ),
        'track_urls': [
            KHINSIDER_BASE_URL + anchor['href']
            for row in soup.select('#songlist tr')
            if (anchor := row.select_one('td a'))
        ],
    }
