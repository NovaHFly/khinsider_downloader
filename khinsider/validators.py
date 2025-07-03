import requests

from .exceptions import ObjectDoesNotExist


def khinsider_object_exists(response: requests.Response) -> None:
    """Check if some object actually exists on page in response.

    :raises ObjectDoesNotExist: No object found on page in respone.
    """
    if 'Ooops!' not in response.text:
        return

    url = str(response.url)
    raise ObjectDoesNotExist(f'Requested object does not exist: {url}')
