from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import unquote

from .constants import ALBUM_BASE_URL


@dataclass
class AudioTrack:
    album: 'Album' = field(repr=False)
    page_url: str
    mp3_url: str = field(repr=False)

    def __str__(self) -> str:
        return f'{self.album.slug} - {self.filename}'

    @cached_property
    def filename(self) -> str:
        return unquote(unquote(self.page_url.rsplit('/')[-1]))


@dataclass
class Album:
    name: str
    slug: str

    thumbnail_urls: Sequence[str]

    year: str
    type: str

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
class AlbumSearchResult:
    name: str
    type: str
    year: str

    slug: str
