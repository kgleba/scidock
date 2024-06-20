import re
from functools import cache
from typing import Any

import grequests

__all__ = ('extract_dois', 'extract_arxiv_ids', 'extract_names', 'extract_keywords', 'simplify_query', 'clear_query')

NLP_SERVER = 'https://kgleba-scidock-nlp.hf.space'

# following CrossRef's recommendation: https://www.crossref.org/blog/dois-and-matching-regular-expressions
DOI_PATTERN = re.compile(r'10.\d{4,9}/[-._;()/:a-zA-Z0-9]+')

# source: https://info.arxiv.org/help/arxiv_identifier_for_services.html
ARXIV_PATTERN = re.compile(r'(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?')

remote_data = {}


def _retrieve_remote_data(query: str, operation: str) -> Any:
    if remote_data.get(query) is None:
        request_labels = ('extract_names', 'extract_keywords', 'remove_stop_words')
        requests = [
            grequests.post(f'{NLP_SERVER}/extract_names', json={'query': query}),
            grequests.post(f'{NLP_SERVER}/extract_keywords', json={'query': query}),
            grequests.post(f'{NLP_SERVER}/remove_stop_words', json={'query': query})
        ]
        responses = grequests.map(requests)

        remote_data[query] = dict(zip(request_labels, responses))

    response = remote_data[query].get(operation)
    return response.json() if response is not None and response.ok else None


@cache
def extract_dois(query: str) -> list[str]:
    return re.findall(DOI_PATTERN, query)


@cache
def extract_arxiv_ids(query: str) -> list[str]:
    return re.findall(ARXIV_PATTERN, query)


def extract_names(query: str) -> list[str] | None:
    return _retrieve_remote_data(query, 'extract_names')


def extract_keywords(query: str) -> list[str] | None:
    return _retrieve_remote_data(query, 'extract_keywords')


def simplify_query(query: str) -> str | None:
    return _retrieve_remote_data(clear_query(query), 'remove_stop_words')


def clear_query(query: str) -> str:
    dois = extract_dois(query)
    for doi in dois:
        query = re.sub(f' *{doi} *', ' ', query)

    names = extract_names(query)
    if names is not None:
        for name in names:
            query = re.sub(f' *{name} *', ' ', query)

    return query
