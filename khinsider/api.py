from functools import partial

from .constants import KHINSIDER_BASE_URL
from .decorators import cache
from .enums import AlbumTypes
from .models import Album, AlbumShort, Track
from .scraper import (
    scrape_album_page,
    scrape_search_page,
    scrape_track_page,
)
from .search import QueryBuilder


@cache
def get_album(album_slug: str) -> Album:
    """Get album data by its slug.

    :param str album_slug: Album url slug.
    :return Album: Album instance.
    """
    album_url = f'{KHINSIDER_BASE_URL}/game-soundtracks/album/{album_slug}'
    album_json = scrape_album_page(album_url)

    return Album(**album_json)


@cache
def get_track(album_slug: str, track_name: str) -> Track:
    """Get track data by its slug and name.

    Note: name must be extracted from url to work correctly.

    :param str album_slug: Track's album url slug.
    :param str track_name: Track name as in url.
    :return Track: Track instance.
    """
    track_url = (
        f'{KHINSIDER_BASE_URL}/game-soundtracks/album/'
        f'{album_slug}/{track_name}'
    )
    track_json = scrape_track_page(track_url)

    return Track(
        **track_json,
        _album_getter=partial(get_album, album_slug=album_slug),
    )


@cache
def search_albums(
    search_query: str,
    album_type: AlbumTypes = AlbumTypes.EMPTY,
) -> list[AlbumShort]:
    """Search for albums.

    :param str search_query: What to search for.
    :param AlbumTypes: Type of albums to search for.
        Default is EMPTY which means no filtering (for most queries).
    :return list[AlbumShort]: List of search results.
    """
    search_url = f'{KHINSIDER_BASE_URL}/search?{
        (
            QueryBuilder()
            .search_for(search_query)
            .album_type(album_type)
            .build()
        )
    }'

    search_results = scrape_search_page(search_url)
    return [
        AlbumShort(
            **search_result,
            _album_getter=get_album,
        )
        for search_result in search_results
    ]


@cache
def get_publisher_albums(publisher_slug: str):
    """Get all albums publisher by this publisher

    :param str publisher_slug: Publisher url slug.
    :return list[AlbumShort]: List of publisher albums.
    """
    search_url = (
        f'{KHINSIDER_BASE_URL}/game-soundtracks/publisher/{publisher_slug}'
    )

    search_results = scrape_search_page(search_url)
    return [
        AlbumShort(
            **search_result,
            _album_getter=get_album,
        )
        for search_result in search_results
    ]
