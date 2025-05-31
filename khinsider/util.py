from functools import partial
from urllib import quote


def normalize_query(query: str) -> str:
    full_quote = partial(quote, safe='')
    return '+'.join(map(full_quote, query.split()))
