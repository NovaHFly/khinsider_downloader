from functools import partial
from hashlib import md5
from typing import Any
from urllib.parse import quote, unquote

from .constants import KHINSIDER_URL_REGEX
from .exceptions import InvalidUrl


def escape_url_query(query: str) -> str:
    """Quote all url-reserved characters in url query.

    :param str query: Unescaped url query.
    :return str: Escaped url query.
    """
    full_quote = partial(quote, safe='')
    return '+'.join(map(full_quote, query.split()))


def parse_khinsider_url(url: str) -> tuple[str, str]:
    """Extract album slug and track name from khinsider album-track url.

    :param str url: Valid khinsider url under /game-soundtracks/album/ path.
    :return tuple[str, str]: (Album slug, track_name)
    """
    if not (match := KHINSIDER_URL_REGEX.match(url)):
        raise InvalidUrl(f'{url} is not an album or track url from khinsider')

    return match[1], match[2] or ''


def full_unquote(string: str, quote_layers: int = 2) -> str:
    """Unquote string which has escaped html escape characters.

    :param str string: String to url-unquote.
    :param int quote_layers: How many times to apply
        urllib.unquote to the string.
    :return str: Unquoted string.
    """
    for _ in range(quote_layers):
        string = unquote(string)

    return string


def get_object_md5(obj: Any) -> str:
    """Generate md5 hash for an object.

    :param obj: Some object.
    :return str: Object's md5 hash.
    """
    return md5(str(obj).encode()).hexdigest()
