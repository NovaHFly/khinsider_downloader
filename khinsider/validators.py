import requests

from .constants import KHINSIDER_BASE_URL
from .exceptions import InvalidUrl, ObjectDoesNotExist


def url_is_khinsider_url(url: str) -> None:
    if url.startswith(KHINSIDER_BASE_URL):
        return

    raise InvalidUrl(f'Url does not lead to downloads.khinsider.com: {url}')


def url_is_khinsider_object(url: str) -> None:
    url_is_khinsider_url(url)

    cleaned_url = url.removeprefix(KHINSIDER_BASE_URL)

    if cleaned_url.startswith('/game-soundtracks'):
        return

    raise InvalidUrl(f'Url does not lead to soundtrack object: {url}')


def url_is_khinsider_track(url: str) -> None:
    url_is_khinsider_object(url)

    cleaned_url = url.removeprefix(KHINSIDER_BASE_URL + '/game-soundtracks/')

    if len(cleaned_url.split('/')) == 3:
        return

    raise InvalidUrl(f'Url does not lead to track page: {url}')


def url_is_khinsider_album(url: str) -> None:
    url_is_khinsider_object(url)

    cleaned_url = url.removeprefix(KHINSIDER_BASE_URL + '/game-soundtracks/')

    if len(cleaned_url.split('/')) == 2:
        return

    raise InvalidUrl(f'Url does not lead to album page: {url}')


def khinsider_object_exists(response: requests.Response) -> None:
    if 'Ooops!' not in response.text:
        return

    url = str(response.url)
    raise ObjectDoesNotExist(f'Requested object does not exist: {url}')
