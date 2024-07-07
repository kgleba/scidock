from collections.abc import Iterator
from dataclasses import dataclass
from pprint import pformat

import crossref.restful
import requests
from crossref.restful import Etiquette, Works

from scidock.config import logger
from scidock.parsers.mathml_parser import parse_document
from scidock.parsers.query_parser import clear_query, extract_dois, extract_keywords, extract_names, simplify_query
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
        return f'{self.title.rstrip(".")}. DOI: {self.DOI}'


@responsive_cache
def perform_query(*args, **kwargs) -> Works:
    return engine.query(*args, **kwargs)


@responsive_cache
def prepare_query_args(query: str) -> tuple[list[str], dict[str, str]]:
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


def extract_metadata(paper: dict | None) -> CrossRefItem:
    if paper is None:
        paper = {}

    title = ' / '.join(paper.get('title', ('UNTITLED',)))

    if 'xmlns' in title:
        title = parse_document(title)

    return CrossRefItem(title, paper.get('DOI'), paper.get('score', 1000.0))


def search(query: str) -> Iterator[CrossRefItem]:
    plain_query = simplify_query(query)
    search_query = iter(())

    if plain_query.strip():
        keywords, search_params = prepare_query_args(query)
        search_query = perform_query(*keywords, **search_params)

    dois = extract_dois(query)
    for doi in dois:
        paper = engine.doi(doi)
        yield extract_metadata(paper)

    for paper in search_query:
        if None in (paper.get('title'), paper.get('DOI'), paper.get('score')):
            logger.warning(f'Received the paper with an unusual metadata: {pformat(paper)}')

        yield extract_metadata(paper)
