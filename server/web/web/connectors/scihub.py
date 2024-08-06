import asyncio

import aiohttp
import requests
from async_lru import alru_cache
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from yarl import URL

from web.log import logger
from web.parsers.metadata import EmptyLinkMeta, LinkMeta

UA = UserAgent()

# TODO: make mirrors dynamic or more configurable
SCIHUB_MIRRORS = ['https://sci-hub.ru', 'https://sci-hub.se', 'https://sci-hub.st']
SCIDB_MIRRORS = ['https://annas-archive.se/scidb', 'https://annas-archive.org/scidb']


@alru_cache
async def establish_mirror() -> str | None:
    sample_doi = '10.1108/14684520810866010'

    async with aiohttp.ClientSession() as session:
        mirror_ping = [
            session.get(f'{mirror}/{sample_doi}', headers={'User-Agent': UA.random}, timeout=4)
            for mirror in SCIDB_MIRRORS + SCIHUB_MIRRORS
        ]

        ping_results: tuple[aiohttp.ClientResponse | BaseException] = await asyncio.gather(
            *mirror_ping, return_exceptions=True
        )

        mirror = None
        for ping_result in ping_results:
            if isinstance(ping_result, TimeoutError) or not ping_result.ok:
                continue

            if mirror is None or mirror in SCIHUB_MIRRORS:
                # prefer SciDB over Sci-Hub for additional 10M papers
                for scidb_mirror in SCIDB_MIRRORS:
                    if str(ping_result.url).startswith(scidb_mirror):
                        return scidb_mirror

                for scihub_mirror in SCIHUB_MIRRORS:
                    if str(ping_result.url).startswith(scihub_mirror):
                        mirror = scihub_mirror

        if mirror is None:
            mirror_conn_error = RuntimeError(
                'Could not establish connection with any of the Sci-Hub/SciDB mirrors! Try using a proxy'
            )
            logger.opt(exception=mirror_conn_error).critical(str(mirror_conn_error))
            raise mirror_conn_error

        logger.info(f'Established connection with the Sci-Hub {mirror = }')

        return mirror


def _parse_scihub(soup: BeautifulSoup, mirror: str) -> LinkMeta:
    download_button = soup.find('button')
    if download_button is None:
        logger.info(
            f'Did not find the download button in the Sci-Hub {mirror = } (document not found)'
        )
        return EmptyLinkMeta

    if download_button.get('onclick') is None:
        logger.error(
            'Download button does not have an "onclick" attribute (Sci-Hub DOM structure has changed)!'
        )
        return EmptyLinkMeta

    redirect_code = download_button['onclick']
    redirect_location = redirect_code.removeprefix("location.href='").removesuffix("'")
    download_link = ('https:' if redirect_location.startswith('//') else mirror) + redirect_location

    return LinkMeta(download_link, guarantee=True)


def _parse_scidb(soup: BeautifulSoup, mirror: str) -> LinkMeta:
    download_button = soup.find('a', string='Download') or soup.find(
        'a', string='Sci-Hub'
    )  # SciDB supports Sci-Hub as a source
    if download_button is None:
        logger.warning(f'Did not find the download button in the Sci-DB {mirror = }')
        return EmptyLinkMeta

    download_link = download_button['href']

    return LinkMeta(download_link, guarantee=True)


HOST_MAPPING = {URL(mirror).host: _parse_scihub for mirror in SCIHUB_MIRRORS} | {
    URL(mirror).host: _parse_scidb for mirror in SCIDB_MIRRORS
}


async def get_download_link(doi: str) -> LinkMeta:
    if not doi.strip():
        return EmptyLinkMeta

    doi = doi.strip().lower()

    logger.info(f'Attempting to find a file with DOI = {doi} in Sci-Hub DB')
    mirror = await establish_mirror()

    # `aiohttp` cannot be used with Sci-DB as `await preview_page.text()` tries to load the entire page,
    # with embedded PDF - which may not happen at all if the resource is blocked in the region
    # (or happen with a noticeable delay)
    # anyway, we get the same blocking call using `requests` (which correctly handles the behavior described above)
    try:
        preview_page = requests.get(
            f'{mirror}/{doi}', headers={'User-Agent': UA.random}, allow_redirects=False, timeout=4
        )
    except requests.Timeout:
        logger.warning(f'{mirror}/{doi} timed out')
        return EmptyLinkMeta

    mirror = URL(preview_page.url).host
    soup = BeautifulSoup(preview_page.text, 'html.parser')

    parse_function = HOST_MAPPING.get(mirror)
    if parse_function is not None:
        return parse_function(soup, mirror)

    logger.warning(f'Unknown Sci-Hub/SciDB {mirror = }')
    return EmptyLinkMeta
