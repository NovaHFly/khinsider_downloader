class KhinsiderError(Exception):
    """Base class for khinsider errors."""


class InvalidUrl(KhinsiderError):
    """Requested url is invalid."""


class ObjectDoesNotExist(KhinsiderError):
    """Requested object does not exist."""


class NoRequestedDataInHtml(KhinsiderError):
    """Requested data is missing from provided html."""
