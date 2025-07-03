import re
from pathlib import Path

KHINSIDER_BASE_URL = 'https://downloads.khinsider.com'
"""Khinsider domain url with protocol and without trailing slash."""
ALBUM_BASE_URL = f'{KHINSIDER_BASE_URL}/game-soundtracks/album'
"""Base url for all khinsider album pages"""
DOWNLOADS_PATH = Path('downloads')
"""Default file downloads path"""

KHINSIDER_URL_REGEX = re.compile(
    r'https:\/\/downloads\.khinsider\.com\/'
    r'game-soundtracks\/album\/([^\s/]+)\/?([^\s/]+)?'
)
"""
Regex to check if khinsider url is valid
and to extract album slug and track name.
"""

MAX_CONCURRENT_REQUESTS = 5
"""Maximum count of concurrent requests to downloads.khinsider.com"""

CACHE_LIFESPAN_DAYS = 1
"""Maximum number of days cached values are conserved."""

MINUTE_SECONDS = 60
HOUR_SECONDS = 60 * MINUTE_SECONDS
DAY_SECONDS = 24 * HOUR_SECONDS
