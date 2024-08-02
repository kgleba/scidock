import asyncio
from functools import reduce
from math import ceil
from operator import add, itemgetter

import aiohttp

from web.log import logger
from web.parsers.mathml import parse_document
from web.parsers.metadata import SearchMeta
from web.parsers.query import clear_query, extract_dois, extract_keywords, extract_names, remove_stop_words

__all__ = ('search',)

PAGE_SIZE = 100
DATA_LIMIT = 100

CROSSREF_URL = 'https://api.crossref.org/works'


def make_etiquette(tool: str, version: str, project_link: str, mailto: str) -> str:
    return f'{tool}/{version} ({project_link};mailto:{mailto})'


ETIQUETTE = make_etiquette('SciDock', '1.0', 'https://github.com/kgleba/scidock',
                           'kgleba@yandex.ru')


async def _perform_query(url: str, parameters: dict[str, str]) -> list[dict]:
    async with aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.get(url, params=parameters,
                               headers={'User-Agent': ETIQUETTE}) as response:
            if response.status == 404:  # noqa: PLR2004 - 404 as a status code is obvious
                return []

            return await response.json()


def _extract_metadata(paper: dict) -> SearchMeta:
    title = ' / '.join(paper.get('title', ('UNTITLED',)))

    if 'xmlns' in title:
        title = parse_document(title)

    authors = []
    for author in paper.get('author', []):
        name_structure = [author.get(field, '') for field in ('given', 'family', 'name')]
        authors.append(' '.join(name_structure).strip())

    download_link = ''
    for related_link in paper.get('link', []):
        if related_link['content-type'] == 'application/pdf':
            download_link = related_link['URL']
            break

    return SearchMeta(title=title,
                      DOI=paper.get('DOI'),
                      authors=authors,
                      abstract=paper.get('abstract', ''),
                      download_link=download_link,
                      relevance_score=paper.get('score', 1000.0))


async def search(query: str, extended: bool = False) -> list[SearchMeta]:
    plain_query = await remove_stop_words(query)
    if not plain_query.strip():
        return []

    dois = extract_dois(query)

    names = await extract_names(query)
    logger.info(f'Extracted names: {names!r}')

    query = await clear_query(query)
    keywords = await extract_keywords(query)
    logger.info(f'Extracted keywords: {keywords!r}')

    names = ' '.join(names)
    keywords = ' '.join(keywords) if keywords else query

    crossref_results = []
    search_params = {}

    if names:
        search_params['query.author'] = names

    if keywords:
        if extended:
            search_params['query'] = keywords
        else:
            search_params['query.title'] = keywords

    doi_requests = [_perform_query(f'{CROSSREF_URL}/{doi}', {}) for doi in dois]
    doi_requests = await asyncio.gather(*doi_requests)
    doi_requests = list(map(itemgetter('message'), doi_requests))
    crossref_results += doi_requests

    if search_params:
        search_params.update({'sort': 'score', 'order': 'desc'})

        crossref_pages = []
        for page_n in range(ceil(DATA_LIMIT / PAGE_SIZE)):
            search_params.update({'rows': PAGE_SIZE, 'offset': PAGE_SIZE * page_n})
            crossref_pages.append(_perform_query(CROSSREF_URL, search_params))

        crossref_pages = await asyncio.gather(*crossref_pages)
        crossref_pages = list(map(itemgetter('message'), crossref_pages))
        crossref_pages = list(map(itemgetter('items'), crossref_pages))
        crossref_pages = reduce(add, crossref_pages)
        crossref_results += crossref_pages

    crossref_results = list(map(_extract_metadata, crossref_results))

    return crossref_results


async def main():
    logger.error(await search('meow 10.1088/1757-899X/330/1/012064'))
    logger.error(await search(
        'Assessment of Process Capability: the case of Soft Drinks Processing Unit by Kottala Sri Yogi'))


if __name__ == '__main__':
    asyncio.run(main())
