import asyncio
import json
from collections.abc import Iterator
from contextlib import asynccontextmanager
from functools import partial
from itertools import batched

import aiohttp
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

from web.connectors import arxiv, crossref, scihub
from web.log import logger
from web.meta.metadata import EmptyLinkMeta, LinkMeta, SearchMeta, merge_result_link
from web.parsers import publishers
from web.utils import random_chain


@asynccontextmanager
async def lifespan(_: FastAPI):
    await scihub.establish_mirror()
    yield


app = FastAPI(lifespan=lifespan)

PAGE_SIZE = 20


def _merge_search_results(
    query: str, crossref_results: list[SearchMeta], arxiv_results: list[SearchMeta]
) -> list[SearchMeta]:
    # approach of defining the cutoff value for CrossRef relevance scores
    search_prefix = []
    prefix_score_ratios = []
    prefix_max = -1
    previous_score = 0

    crossref_pointer = 0
    arxiv_pointer = 0
    arxiv_ids = arxiv.extract_arxiv_ids(query)

    if arxiv_ids:
        search_prefix += arxiv_results
        arxiv_pointer = len(arxiv_results)

    for search_result in crossref_results:
        search_prefix.append(search_result)
        crossref_pointer += 1

        prefix_max = max(prefix_max, search_result.relevance_score)
        prefix_score_ratios.append((search_result.relevance_score - previous_score) / prefix_max)

        if len(search_prefix) >= 8:  # noqa: PLR2004 - arbitrary number, should be tweaked afterwards
            best_score_ratio = prefix_score_ratios.index(max(prefix_score_ratios[1:]))
            insert_point = best_score_ratio + 2
            search_prefix[insert_point:insert_point] = arxiv_results[
                arxiv_pointer : arxiv_pointer + 5
            ]
            arxiv_pointer += 5

            break

    return search_prefix + list(
        random_chain(crossref_results[crossref_pointer:], arxiv_results[arxiv_pointer:])
    )


async def _get_download_link(search_result: SearchMeta, session: aiohttp.ClientSession) -> LinkMeta:
    if search_result.download_link:
        return LinkMeta(search_result.download_link, guarantee=True)

    if not search_result.DOI.strip():
        return EmptyLinkMeta

    scihub_result = await scihub.get_download_link(search_result.DOI)
    if scihub_result != EmptyLinkMeta:
        return scihub_result

    publishers_result = await publishers.get_download_link(search_result.DOI, session)
    return publishers_result


async def generate_results_with_links(
    search_results: list[SearchMeta], include_abstract: bool
) -> Iterator[list[dict]]:
    links_retrieved = 0

    for results_page in batched(search_results, PAGE_SIZE):
        async with aiohttp.ClientSession() as session:
            get_download_link = partial(_get_download_link, session=session)
            page_links = await asyncio.gather(*map(get_download_link, results_page))

            links_retrieved += len([link for link in page_links if link != EmptyLinkMeta])

            results_links = [
                merge_result_link(result, link, include_abstract)
                for result, link in zip(results_page, page_links, strict=True)
            ]

            yield json.dumps(results_links)

    logger.info(
        f'Retrieved {links_retrieved} links for {len(search_results)} search results. '
        f'Ratio: {round(links_retrieved / len(search_results), 3)}'
    )


@app.get('/search')
async def search(
    query: str,
    extended: bool = False,
    attempt_download: bool = True,
    include_abstract: bool = False,
):
    logger.info(f'Got search request with {extended = } {query = !r} and {attempt_download = }')

    crossref_results, arxiv_results = await asyncio.gather(
        crossref.search(query, extended), arxiv.search(query, extended)
    )
    search_results = _merge_search_results(query, crossref_results, arxiv_results)

    if attempt_download:
        return EventSourceResponse(generate_results_with_links(search_results, include_abstract))

    return [merge_result_link(result, EmptyLinkMeta, include_abstract) for result in search_results]
