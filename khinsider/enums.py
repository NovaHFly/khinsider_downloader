from enum import StrEnum


class AlbumTypes(StrEnum):
    EMPTY = '0'
    """Mostly arrangements only, can catch some from other groups."""
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
