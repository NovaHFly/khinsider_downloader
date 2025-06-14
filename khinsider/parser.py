import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .constants import KHINSIDER_BASE_URL
from .util import parse_khinsider_url

logger = logging.getLogger('khinsider-parser')


def parse_track_data(html_text: str) -> dict[str, str]:
    match = re.search(r'<audio.+src="(.+)"', html_text)

    logger.debug(f'parse_track_data:{match = }')

    if not match:
        return {}

    return {'mp3_url': match[1]}


def parse_album_data(html_text: str) -> dict[str, Any]:
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


def parse_publisher_data(html_text: str) -> dict[str, str]:
    match = re.search(r'Published by:.+<a href=".+/(.+)">(.+)</a>', html_text)

    logger.debug(f'parse_publisher_data:{match = }')

    if not match:
        return {}

    return {
        'name': match[2],
        'slug': match[1],
    }


def parse_search_page(html_text: str) -> list[dict[str, str]]:
    def _parse_table_row(row_tag: Tag) -> dict[str, str]:
        col_tags = row_tag.select('td')[1:]

        name_anchor = col_tags[0].select_one('a')
        album_name = name_anchor.text

        album_url = KHINSIDER_BASE_URL + name_anchor.attrs['href']
        album_slug = parse_khinsider_url(album_url)[0]

        album_type = col_tags[2].text
        album_year = col_tags[3].text

        return {
            'name': album_name,
            'type': album_type,
            'year': album_year,
            'slug': album_slug,
        }

    soup = BeautifulSoup(html_text, 'lxml')

    if not (result_tags := soup.select('table.albumList tr')[1:]):
        return []

    return [_parse_table_row(tag) for tag in result_tags]
