from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pprint import pformat

import crossref.restful
import requests
from crossref.restful import Etiquette, Works

from scidock.config import logger
from scidock.search_engines.query_parser import clear_query, extract_dois, extract_keywords, extract_names, simplify_query
from scidock.utils import responsive_cache

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


@responsive_cache
def _perform_query(*args, **kwargs) -> Works:
    return engine.query(*args, **kwargs)


@responsive_cache
def _prepare_query_args(query: str) -> tuple[list[str], dict[str, str]]:
    search_params = {}

    names = extract_names(query)
    logger.info(f'Extracted names: {names!r}')
    if names is not None:
        search_params['author'] = ' '.join(names)

    query = clear_query(query)
    keywords = extract_keywords(query)
    logger.info(f'Extracted keywords: {keywords!r}')
    if not keywords:
        keywords = [query]

    return keywords, search_params


def search(query: str) -> tuple[int, Iterator[CrossRefItem]]:
    plain_query = simplify_query(query)
    if not plain_query.strip():
        return 0, iter([])

    keywords, search_params = _prepare_query_args(query)
    search_query = _perform_query(*keywords, **search_params)
    search_iter = iter(search_query)

    logger.info('Launching concurrent requests')
    with ThreadPoolExecutor() as pool:
        count_future = pool.submit(search_query.count)
        search_future = pool.submit(next, search_iter)

        n_search_results = count_future.result()
        first_search_result = search_future.result()

    def retrieve_papers() -> Iterator[CrossRefItem]:
        dois = extract_dois(query)
        for doi in dois:
            paper = engine.doi(doi)

            if 'xmlns' in ''.join(paper.get('title', ())):
                logger.warning(
                    'CrossRef responses might have MathML in metadata elements (such as title), which might lead to the parsing errors. '
                    'See: https://www.crossref.org/documentation/schema-library/markup-guide-metadata-segments/mathml. '
                    'I\'m aware of the issue and working on transforming it into the printable math format.')

            yield CrossRefItem(' / '.join(paper.get('title', ('UNTITLED',))), paper['DOI'])

        yield CrossRefItem(' / '.join(first_search_result.get('title', ('UNTITLED',))), first_search_result['DOI'],
                           first_search_result['score'])

        for paper in search_iter:
            if None in (paper.get('title'), paper.get('DOI'), paper.get('score')):
                logger.warning(f'Received the paper with an unusual metadata: {pformat(paper)}')

            if 'xmlns' in ''.join(paper.get('title', ())):
                logger.warning(
                    'CrossRef responses might have MathML in metadata elements (such as title), which might lead to the parsing errors. '
                    'See: https://www.crossref.org/documentation/schema-library/markup-guide-metadata-segments/mathml. '
                    'I\'m aware of the issue and working on transforming it into the printable math format.')

            yield CrossRefItem(' / '.join(paper.get('title', ('UNTITLED',))), paper['DOI'], paper['score'])

    return n_search_results, next(iter(retrieve_papers, None))
