import asyncio
from functools import reduce
from math import ceil
from operator import add

import aiohttp
from fake_useragent import UserAgent

from web.log import logger
from web.parsers.atom import check_content_presence, extract_metadata
from web.parsers.metadata import SearchMeta
from web.parsers.query import clear_query, extract_arxiv_ids, extract_names

__all__ = ('search',)

UA = UserAgent()

PAGE_SIZE = 50
DATA_LIMIT = 100
MAX_RETRIES = 3

ARXIV_URL = 'https://export.arxiv.org/api/query'


async def _perform_query(url: str, parameters: dict[str, str | int]) -> str:
    logger.info(f'Performing arXiv search query with {parameters = }')

    result_xml = ''
    attempts = 0

    async with aiohttp.ClientSession() as session:
        while attempts < MAX_RETRIES and (not result_xml or not check_content_presence(result_xml)):
            async with session.get(url, params=parameters,
                                   headers={'User-Agent': UA.random}) as response:
                result_xml = await response.text()

            attempts += 1

        if not check_content_presence(result_xml):
            logger.debug(f'Given up on {attempts = }')
        else:
            logger.debug(f'Succeeded with {attempts = }')

    return result_xml


async def search(query: str, extended: bool = False) -> list[SearchMeta]:
    arxiv_ids = extract_arxiv_ids(query)
    logger.info(f'Extracted arXiv IDs: {arxiv_ids!r}')

    if arxiv_ids:
        id_list = ','.join(arxiv_ids)
        arxiv_results = await _perform_query(ARXIV_URL, {'id_list': id_list})
        return extract_metadata(arxiv_results)

    search_query = ''

    names = await extract_names(query)
    logger.info(f'Extracted names: {names!r}')
    if names:
        search_query += 'au:' + ' AND '.join(names)

    # TODO: do something clever with extracting titles

    search_query += ('all:' if extended else 'ti:') + await clear_query(query)

    arxiv_pages = []
    for page_n in range(ceil(DATA_LIMIT / PAGE_SIZE)):
        arxiv_pages.append(_perform_query(ARXIV_URL,
                                          {'search_query': search_query,
                                           'start': PAGE_SIZE * page_n,
                                           'max_results': PAGE_SIZE,
                                           'sortBy': 'relevance',
                                           'sortOrder': 'descending'}))

    arxiv_results = await asyncio.gather(*arxiv_pages)
    arxiv_results = reduce(add, list(map(extract_metadata, arxiv_results)))

    return arxiv_results


async def main():
    search_res = await search('deep learning for symbolic computations')
    print(len(search_res))
    print(search_res[:10])


if __name__ == '__main__':
    asyncio.run(main())
