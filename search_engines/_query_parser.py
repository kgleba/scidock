import re
from functools import cache

import requests

NLP_SERVER = 'https://kgleba-scidock-nlp.hf.space'
nlp_session = requests.Session()

# following CrossRef's recommendation: https://www.crossref.org/blog/dois-and-matching-regular-expressions
DOI_PATTERN = re.compile(r'10.\d{4,9}/[-._;()/:a-zA-Z0-9]+')

# source: https://info.arxiv.org/help/arxiv_identifier_for_services.html
ARXIV_PATTERN = re.compile(r'(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?')


@cache
def extract_names(query: str) -> list[str] | None:
    response = nlp_session.post(f'{NLP_SERVER}/extract_names', json={'query': query})
    return response.json() if response.ok else None


@cache
def extract_keywords(query: str, n_samples: int = 5) -> list[str] | None:
    response = nlp_session.post(f'{NLP_SERVER}/extract_keywords', json={'query': query, 'n_samples': n_samples})
    return response.json() if response.ok else None


@cache
def extract_dois(query: str) -> list[str] | None:
    dois = re.findall(DOI_PATTERN, query)
    return dois if dois else None


@cache
def extract_arxiv_ids(query: str) -> list[str] | None:
    arxiv_ids = re.findall(ARXIV_PATTERN, query)
    return arxiv_ids if arxiv_ids else None


@cache
def clear_query(query: str) -> str:
    dois = extract_dois(query)
    if dois is not None:
        for doi in dois:
            query = re.sub(f' *{doi} *', ' ', query)

    names = extract_names(query)
    if names is not None:
        for name in names:
            query = re.sub(f' *{name} *', ' ', query)

    return query


@cache
def simplify_query(query: str) -> str:
    response = nlp_session.post(f'{NLP_SERVER}/remove_stop_words', json={'query': clear_query(query)})
    return response.json() if response.ok else None
