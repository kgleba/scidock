from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cache

import crossref.restful
import requests
from crossref.restful import Etiquette, Works

from .query_parser import clear_query, extract_dois, extract_keywords, extract_names, simplify_query

crossref.restful.requests = requests.Session()

__all__ = ('search',)

etiquette = Etiquette('SciDock', '0.1.0', 'https://github.com/kgleba/scidock', 'kgleba@yandex.ru')
engine = Works(etiquette=etiquette)


@dataclass
class CrossRefItem:
    title: str
    DOI: str
    relevance_score: float = 1000.0

    def __str__(self):
        return f'{self.title.rstrip('.')}. DOI: {self.DOI}'


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


def search(query: str) -> tuple[int, Iterator[CrossRefItem]] | None:
    plain_query = simplify_query(query)
    if not plain_query.strip():
        return None

    keywords, search_params = _prepare_query_args(query)
    search_query = _perform_query(*keywords, **search_params)
    search_iter = iter(search_query)

    with ThreadPoolExecutor() as pool:
        count_future = pool.submit(search_query.count)
        search_future = pool.submit(next, search_iter)

        n_search_results = count_future.result()
        first_search_result = search_future.result()

    def retrieve_papers() -> Iterator[CrossRefItem]:
        dois = extract_dois(query)
        for doi in dois:
            paper = engine.doi(doi)
            yield CrossRefItem(' / '.join(paper['title']), paper['DOI'])

        yield CrossRefItem(' / '.join(first_search_result['title']), first_search_result['DOI'], first_search_result['score'])

        for paper in search_iter:
            yield CrossRefItem(' / '.join(paper['title']), paper['DOI'], paper['score'])

    return n_search_results, next(iter(retrieve_papers, None))
