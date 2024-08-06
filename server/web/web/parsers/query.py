import re

from web.connectors.nlp import extract_keywords, extract_names, remove_stop_words
from web.utils import responsive_cache

__all__ = (
    'DOI_PATTERN',
    'ARXIV_PATTERN',
    'extract_dois',
    'extract_arxiv_ids',
    'extract_keywords',
    'extract_names',
    'remove_stop_words',
    'clear_query',
)

# following CrossRef's recommendation: https://www.crossref.org/blog/dois-and-matching-regular-expressions
DOI_PATTERN = re.compile(r'10.\d{4,9}/[-._;()/:a-zA-Z0-9]+')

# source: https://info.arxiv.org/help/arxiv_identifier_for_services.html
ARXIV_PATTERN = re.compile(r'(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?')
STRICT_ARXIV_PATTERN = re.compile(rf'arXiv\.{ARXIV_PATTERN.pattern}')


@responsive_cache
def extract_dois(query: str) -> list[str]:
    return re.findall(DOI_PATTERN, query)


@responsive_cache
def extract_arxiv_ids(query: str, strict: bool = False, allow_overlap: bool = False) -> list[str]:
    if not allow_overlap:
        dois = extract_dois(query)
        for doi in dois:
            query = re.sub(f' *{doi} *', ' ', query)

    pattern = STRICT_ARXIV_PATTERN if strict else ARXIV_PATTERN

    return [''.join(match) for match in re.findall(pattern, query)]


async def clear_query(query: str) -> str:
    dois = extract_dois(query)
    for doi in dois:
        query = re.sub(f' *{doi} *', ' ', query)

    arxiv_ids = extract_arxiv_ids(query)
    for arxiv_id in arxiv_ids:
        query = re.sub(f' *{arxiv_id} *', ' ', query)

    names = await extract_names(query)
    if names:
        for name in names:
            query = re.sub(f' *{name} *', ' ', query)

    return query
