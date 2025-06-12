from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import unquote

from .constants import ALBUM_BASE_URL
from .util import parse_khinsider_url, full_unquote


@dataclass
class Publisher:
    name: str
    slug: str

    def __str__(self) -> str:
        return f'Uploader "{self.name}"'


@dataclass
class AudioTrack:
    album: 'Album' = field(repr=False)
    page_url: str
    mp3_url: str = field(repr=False)

    def __str__(self) -> str:
        return f'{self.album.slug} - {self.filename}'

    @cached_property
    def filename(self) -> str:
        return full_unquote(parse_khinsider_url(self.page_url)[1])


@dataclass
class Album:
    name: str
    slug: str

    # TODO: Rename to album_picture_urls
    thumbnail_urls: Sequence[str]

    year: str
    type: str
    publisher: Publisher | None

    track_urls: list[str] = field(
        repr=False,
        default_factory=list,
    )

    @property
    def track_count(self) -> int:
        return len(self.track_urls)

    @property
    def url(self) -> str:
        return f'{ALBUM_BASE_URL}/{self.slug}'


@dataclass
class AlbumShort:
    name: str
    type: str
    year: str
    slug: str
