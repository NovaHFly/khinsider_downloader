from typing import Self

from .util import normalize_query


class QueryBuilder:
    def __init__(self):
        # TODO: album category, sort by
        self._search = ''
        self._year = ''
        self._type = ''

    def search_for(self, query: str) -> Self:
        self._search = normalize_query(query)
        return self

    def album_year(self, year: str) -> Self:
        self._year = year
        return self

    def album_type(self, type_: str) -> Self:
        self._type = type_
        return self

    def build(self) -> str:
        query = (
            f'search={self._search}'
            f'&album_year={self._year}'
            f'&album_type={self._type}'
        )
        return query
