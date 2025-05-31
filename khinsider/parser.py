import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .constants import KHINSIDER_BASE_URL


def parse_track_page(html_text: str) -> dict[str, str]:
    soup = BeautifulSoup(html_text, 'lxml')
    return {'mp3_url': soup.select_one('audio')['src']}


def parse_album_page(html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text, 'lxml')
    return {
        'name': soup.select_one('h2').text,
        'thumbnail_urls': [
            anchor.attrs['href'] for anchor in soup.select('.albumImage a')
        ],
        'year': (
            match[1]
            if (match := re.search(r'Year: <b.(\d{4})</b>', html_text))
            else None
        ),
        'type': (
            tag.text if (tag := soup.select_one('p[align=left] b a')) else None
        ),
        'track_urls': [
            KHINSIDER_BASE_URL + anchor['href']
            for row in soup.select('#songlist tr')
            if (anchor := row.select_one('td a'))
        ],
    }


def parse_album_search_result(result_tag: Tag) -> dict[str, str]:
    col_tags = result_tag.select('td')[1:]

    name_anchor = col_tags[0].select_one('a')
    album_name = name_anchor.text
    album_url = KHINSIDER_BASE_URL + name_anchor.attrs['href']
    album_type = col_tags[2].text
    album_year = col_tags[3].text

    return {
        'name': album_name,
        'type': album_type,
        'year': album_year,
        'url': album_url,
    }
