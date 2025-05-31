class KhinsiderError(Exception):
    """Base class for khinsider errors."""


class InvalidUrl(Exception):
    """Requested url is invalid."""


class ObjectDoesNotExist(KhinsiderError):
    """Requested object does not exist."""
