from functools import partial
from urllib.parse import quote, unquote

from constants import KHINSIDER_URL_REGEX

from .exceptions import InvalidUrl


def normalize_query(query: str) -> str:
    full_quote = partial(quote, safe='')
    return '+'.join(map(full_quote, query.split()))


def parse_khinsider_url(url: str) -> tuple[str, str | None]:
    """Extract album slug and track name from khinsider album-track url.

    Args:
        url (str): Valid khinsider url under /game-soundtracks/album/ path.

    Returns:
        out (tuple[str, str|None]): album_slug, track_name;
    """
    if not (match := KHINSIDER_URL_REGEX.match(url)):
        raise InvalidUrl(f'{url} is not an album or track url from khinsider')

    return match[1], match[2]


def full_unquote(in_: str, quote_layers: int = 2) -> str:
    """Unquote string which has escaped html escape characters."""
    for _ in range(quote_layers):
        in_ = unquote(in_)

    return in_
