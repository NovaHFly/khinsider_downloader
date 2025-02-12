class KhinsiderError(Exception):
    """Base class for khinsider errors."""


class InvalidUrl(Exception):
    """Requested url is invalid."""


class ItemDoesNotExist(KhinsiderError):
    """Requested item does not exist."""
