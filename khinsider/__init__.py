"""Music downloader.

Downloads music from downloads.khinsider.py

Available sub-modules:
-
"""

from .cache import CacheManager
from .constants import (
    ALBUM_BASE_URL,
    DOWNLOADS_PATH,
    KHINSIDER_BASE_URL,
    KHINSIDER_URL_REGEX,
    MAX_CONCURRENT_REQUESTS,
)
from .exceptions import (
    InvalidUrl,
    KhinsiderError,
    ObjectDoesNotExist,
)
from .files import (
    download_many,
    download_track_file,
)
from .models import (
    Album,
    AlbumShort,
    AudioTrack,
)
from .scraper import (
    fetch_tracks,
    get_album,
    get_publisher_albums,
    get_track,
    search_albums,
)
from .util import (
    parse_khinsider_url,
)

__all__ = [
    'ALBUM_BASE_URL',
    'DOWNLOADS_PATH',
    'KHINSIDER_BASE_URL',
    'KHINSIDER_URL_REGEX',
    'MAX_CONCURRENT_REQUESTS',
    'Album',
    'AlbumShort',
    'AudioTrack',
    'CacheManager',
    'InvalidUrl',
    'KhinsiderError',
    'ObjectDoesNotExist',
    'download_many',
    'download_track_file',
    'fetch_tracks',
    'get_album',
    'get_publisher_albums',
    'get_track',
    'parse_khinsider_url',
    'search_albums',
]
