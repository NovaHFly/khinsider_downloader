from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from json import JSONEncoder
from typing import Protocol

from .constants import ALBUM_BASE_URL
from .util import full_unquote, parse_khinsider_url


class BaseModel(Protocol):
    def to_json(self) -> dict: ...


class KhinsiderJSONEncoder(JSONEncoder):
    def default(self, o: BaseModel):
        try:
            return o.to_json()
        except AttributeError:
            return super().default(o)


@dataclass
class Publisher:
    name: str
    slug: str

    def __str__(self) -> str:
        return f'Uploader "{self.name}"'

    def to_json(self) -> dict[str, str]:
        return {
            'name': self.name,
            'slug': self.slug,
        }


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

    def to_json(self) -> dict:
        return {
            'album': self.album.to_json(),
            'page_url': self.page_url,
            'mp3_url': self.mp3_url,
        }


@dataclass
class AlbumShort:
    name: str
    type: str
    year: str
    slug: str

    @property
    def url(self) -> str:
        return f'{ALBUM_BASE_URL}/{self.slug}'

    def to_json(self) -> dict[str, str]:
        return {
            'name': self.name,
            'type': self.type,
            'year': self.year,
            'slug': self.slug,
        }


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

    def to_json(self) -> dict:
        return {
            'name': self.name,
            'slug': self.slug,
            'thumbnail_urls': list(self.thumbnail_urls),
            'year': self.year,
            'type': self.type,
            'publisher': self.publisher.to_json(),
        }
