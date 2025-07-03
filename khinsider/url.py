from typing import Self

from .enums import AlbumTypes
from .util import escape_url_query


class QueryBuilder:
    """Simple builder for url queries.

    Handles all underlying formatting.
    """

    def __init__(self):
        # TODO: album category, sort by
        self._search = ''
        self._year = ''
        self._type = AlbumTypes.EMPTY

    def search_for(self, query: str) -> Self:
        """Add search query.

        :params str query: What to search for.
        """
        self._search = escape_url_query(query)
        return self

    def album_year(self, year: str) -> Self:
        """Add an album year to query.

        :param str year: Album year.
        """
        self._year = year
        return self

    def album_type(self, type_: AlbumTypes) -> Self:
        """Add album type to query.

        :param str type_: Album type.
        """
        self._type = type_
        return self

    def build(self) -> str:
        """Build url query.

        :return str: Url query.
        """
        query = (
            f'search={self._search}'
            f'&album_year={self._year}'
            f'&album_type={self._type.value}'
        )
        return query
