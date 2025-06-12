from pathlib import Path

KHINSIDER_BASE_URL = 'https://downloads.khinsider.com'
ALBUM_BASE_URL = f'{KHINSIDER_BASE_URL}/game-soundtracks/album'
DOWNLOADS_PATH = Path('downloads')

DEFAULT_THREAD_COUNT = 6

KHINSIDER_URL_REGEX = (
    r'https:\/\/downloads\.khinsider\.com\/'
    r'game-soundtracks\/album\/([\w%.-]+)\/?([\w%.-]+)?'
)

MAX_CONCURRENT_REQUESTS = 5
