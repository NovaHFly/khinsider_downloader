from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable

from .constants import ALBUM_BASE_URL
from .types import PublisherJson
from .util import full_unquote, parse_khinsider_url


@dataclass
class Publisher:
    """Some music publisher."""

    name: str
    slug: str

    def __str__(self) -> str:
        return f'Publisher "{self.name}"'


@dataclass
class Track:
    """Some music track from khinsider."""

    page_url: str
    mp3_url: str = field(repr=False)

    _album_getter: Callable[[], Album]

    def __str__(self) -> str:
        return f'{self.album.slug} - {self.filename}'

    @cached_property
    def album(self) -> Album:
        """Album to which track belongs."""
        return self._album_getter()

    @cached_property
    def filename(self) -> str:
        """Track's human-readable filename."""
        return full_unquote(parse_khinsider_url(self.page_url)[1])


@dataclass
class AlbumShort:
    """Album short data used for search results."""

    title: str
    type: str | None
    year: str | None
    slug: str

    _album_getter: Callable[[str], Album]

    @cached_property
    def album(self) -> Album:
        """Full version of album data."""
        return self._album_getter(self.slug)


@dataclass
class Album:
    """Some album from khinsider."""

    title: str
    slug: str

    album_art: Sequence[str]

    year: str | None
    type: str | None
    _publisher: PublisherJson | None

    track_urls: list[str] = field(
        repr=False,
        default_factory=list,
    )

    @property
    def track_count(self) -> int:
        """Album track count."""
        return len(self.track_urls)

    @property
    def url(self) -> str:
        """Album page url."""
        return f'{ALBUM_BASE_URL}/{self.slug}'

    @cached_property
    def publisher(self) -> Publisher | None:
        """Publisher which published this album."""
        if not self._publisher:
            return None
        return Publisher(**self._publisher)
