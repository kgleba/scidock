from functools import cache
from typing import Iterator

import grequests
from crossref.restful import Etiquette, Works

from ._query_parser import clear_query, extract_dois, extract_keywords, extract_names, simplify_query

__all__ = ('search', 'search_results_length')

etiquette = Etiquette('SciDock', '0.1.0', 'https://github.com/kgleba/scidock', 'kgleba@yandex.ru')
engine = Works(etiquette=etiquette)


@cache
def _perform_query(*args, **kwargs) -> Works:
    return engine.query(*args, **kwargs)


@cache
def _prepare_query_args(query: str) -> tuple[list[str], dict[str, str]]:
    search_params = {}

    names = extract_names(query)
    if names is not None:
        search_params['author'] = ' '.join(names)

    query = clear_query(query)
    keywords = extract_keywords(query)
    if not keywords:
        keywords = [query]

    return keywords, search_params


def search(query: str) -> Iterator[dict]:
    dois = extract_dois(query)
    for doi in dois:
        yield engine.doi(doi)

    plain_query = simplify_query(query)
    if not plain_query.strip():
        return

    keywords, search_params = _prepare_query_args(query)
    search_query = _perform_query(*keywords, **search_params)
    for paper_metadata in search_query:
        yield paper_metadata


def search_results_length(query: str) -> int:
    plain_query = simplify_query(query)
    if not plain_query.strip():
        return 0

    keywords, search_params = _prepare_query_args(query)
    search_query = _perform_query(*keywords, **search_params)

    return search_query.count()
