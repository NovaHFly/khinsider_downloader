from enum import StrEnum


class AlbumTypes(StrEnum):
    """Album types available on downloads.khinsider.com."""

    EMPTY = '0'
    """No filtering. For some queries might not return full results.
    In such cases better to use one of options below.
    """
    SOUNDTRACKS = '1'
    """Soundtracks only."""
    GAMERIPS = '2'
    """Gamerips only."""
    SINGLES = '3'
    """Singles only."""
    REMIXES = '4'
    """Remixes only."""
    ARRANGEMENTS = '5'
    """Arrangements only."""
    COMPILATIONS = '6'
    """Compilations only."""
    INSPIRED_BY = '7'
    """Inspired by only."""
