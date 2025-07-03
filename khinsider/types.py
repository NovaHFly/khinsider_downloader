from __future__ import annotations

from typing import TypedDict


class AlbumBaseJson(TypedDict):
    title: str
    slug: str
    year: str | None
    type: str | None


class AlbumPageJson(AlbumBaseJson):
    album_art: list[str]
    track_urls: list[str]
    _publisher: PublisherJson | None


class PublisherJson(TypedDict):
    name: str
    slug: str


class TrackJson(TypedDict):
    page_url: str
    mp3_url: str
