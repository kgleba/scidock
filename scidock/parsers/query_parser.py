import re
from typing import Any

import requests

from scidock.ui import progress_bar
from scidock.utils import responsive_cache

__all__ = ('extract_dois', 'extract_arxiv_ids', 'extract_names', 'extract_keywords', 'simplify_query', 'clear_query')

NLP_SERVER = 'https://kgleba-scidock-nlp.hf.space'

# following CrossRef's recommendation: https://www.crossref.org/blog/dois-and-matching-regular-expressions
DOI_PATTERN = re.compile(r'10.\d{4,9}/[-._;()/:a-zA-Z0-9]+')

# source: https://info.arxiv.org/help/arxiv_identifier_for_services.html
ARXIV_PATTERN = re.compile(r'(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?')
STRICT_ARXIV_PATTERN = re.compile(fr'arXiv\.{ARXIV_PATTERN.pattern}')

remote_data = {}


def _retrieve_remote_data(query: str, operation: str) -> Any:
    # updates relevant info about the `query` itself and `clear_query(query)`
    if remote_data.get(query) is None:
        progress_bar.update('Parsing your query using AI...')

        response = requests.post(f'{NLP_SERVER}/complex_analysis', json={'query': query}, timeout=10)
        remote_data.update(response.json())

        progress_bar.revert_status()

    return remote_data[query].get(operation)


@responsive_cache
def extract_dois(query: str) -> list[str]:
    return re.findall(DOI_PATTERN, query)


@responsive_cache
def extract_arxiv_ids(query: str, strict: bool = False, allow_overlap: bool = False) -> list[str]:
    if not allow_overlap:
        dois = extract_dois(query)
        for doi in dois:
            query = re.sub(f' *{doi} *', ' ', query)

    pattern = ARXIV_PATTERN
    if strict:
        pattern = STRICT_ARXIV_PATTERN

    return [''.join(match) for match in re.findall(pattern, query)]


def extract_names(query: str) -> list[str] | None:
    return _retrieve_remote_data(query, 'extract_names')


def extract_keywords(query: str) -> list[str] | None:
    return _retrieve_remote_data(query, 'extract_keywords')


def simplify_query(query: str) -> str | None:
    return _retrieve_remote_data(clear_query(query), 'remove_stop_words')


@responsive_cache
def clear_query(query: str) -> str:
    dois = extract_dois(query)
    for doi in dois:
        query = re.sub(f' *{doi} *', ' ', query)

    arxiv_ids = extract_arxiv_ids(query)
    for arxiv_id in arxiv_ids:
        query = re.sub(f' *{arxiv_id} *', ' ', query)

    names = extract_names(query)
    if names is not None:
        for name in names:
            query = re.sub(f' *{name} *', ' ', query)

    return query
