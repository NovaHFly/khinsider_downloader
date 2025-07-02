from typing import Self

from .enums import AlbumTypes
from .util import format_url_query


class QueryBuilder:
    def __init__(self):
        # TODO: album category, sort by
        self._search = ''
        self._year = ''
        self._type = AlbumTypes.EMPTY

    def search_for(self, query: str) -> Self:
        self._search = format_url_query(query)
        return self

    def album_year(self, year: str) -> Self:
        self._year = year
        return self

    def album_type(self, type_: AlbumTypes) -> Self:
        self._type = type_
        return self

    def build(self) -> str:
        query = (
            f'search={self._search}'
            f'&album_year={self._year}'
            f'&album_type={self._type.value}'
        )
        return query
