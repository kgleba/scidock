import asyncio
import json
import re

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from web.log import logger
from web.parsers.metadata import EmptyLinkMeta, LinkMeta
from web.parsers.query import ARXIV_PATTERN

UA = UserAgent()

# a list of publishers who are known to provide only private access to their works
# blacklist should be made more configurable in the future
PUBLISHER_BLACKLIST = [
    '10.1016',  # Elsevier
    '10.1007',  # Springer
    '10.1201',  # Taylor & Francis
    '10.4324',  # Taylor & Francis
]


async def _get_publisher_page(
    doi: str, session: aiohttp.ClientSession
) -> aiohttp.ClientResponse | None:
    try:
        async with asyncio.timeout(2):
            return await session.get(f'https://doi.org/{doi}', headers={'User-Agent': UA.random})
    except (TimeoutError, aiohttp.client_exceptions.ClientConnectorError):
        logger.warning(f"Publisher's page timed out for {doi = }")
        return None


def _analyze_generic_content(soup: BeautifulSoup, publisher_url: str) -> LinkMeta:
    positive_patterns = [r'\bdownload\b', 'PDF']  # , 'Open Access']
    negative_patterns = [
        'only available via PDF',
        'PDF is available to Subscribers',
        'Get Access',
    ]  # , 'Institutional Access']

    positive_patterns = [re.compile(pattern, flags=re.IGNORECASE) for pattern in positive_patterns]
    negative_patterns = [re.compile(pattern, flags=re.IGNORECASE) for pattern in negative_patterns]

    positive_matches = [soup.find(string=pattern) is not None for pattern in positive_patterns]
    negative_matches = [soup.find(string=pattern) is not None for pattern in negative_patterns]

    # TODO: adjust positive/negative matches policies
    #  (whether presence of only one negative match should dismiss the entire result)

    if any(positive_matches) and not any(negative_matches):
        return LinkMeta(publisher_url, guarantee=False)

    return EmptyLinkMeta


async def get_download_link(doi: str, session: aiohttp.ClientSession) -> LinkMeta:
    if doi.startswith('10.48550'):
        arxiv_id = re.match(rf'10\.48550/arXiv.({ARXIV_PATTERN.pattern})', doi).group(1)
        return LinkMeta(f'https://arxiv.org/pdf/{arxiv_id}', guarantee=True)

    logger.info(f'Attempting to follow a DOI redirect with DOI = {doi}')

    publisher_id = doi.split('/')[0]
    if publisher_id in PUBLISHER_BLACKLIST:
        logger.info(f'DOI redirected to a page of a known blacklisted publisher: {publisher_id}')
        return EmptyLinkMeta

    publisher_page = await _get_publisher_page(doi, session)
    if publisher_page is None:
        return EmptyLinkMeta

    soup = BeautifulSoup(await publisher_page.text(encoding='latin-1'), 'html.parser')

    # for compatibility with `requests` implementation
    # `__str__` is chosen instead of `human_repr`
    publisher_url = str(publisher_page.url)

    if publisher_page.headers.get('Content-Type') in (
        'application/pdf',
        'application/octet-stream',
    ):
        logger.info('DOI redirected to a page with plain PDF')

        return LinkMeta(publisher_url, guarantee=True)

    download_link_meta = EmptyLinkMeta

    if doi.startswith('10.1109'):  # IEEE publisher
        logger.info('DOI redirected to a page of a known publisher: IEEE')

        metadata_pattern = re.compile(
            r'xplGlobal.document.metadata=(.*?});', re.MULTILINE | re.DOTALL
        )
        script = soup.find('script', string=metadata_pattern)
        if script is None:
            return EmptyLinkMeta

        metadata = json.loads(metadata_pattern.search(script.string).group(1))

        download_link = 'https://ieeexplore.ieee.org' + metadata['pdfPath']
        download_link = download_link.replace('iel', 'ielx')  # might be unstable

        download_link_meta = LinkMeta(download_link, guarantee=True)

    if doi.startswith('10.5772'):  # IntechOpen publisher
        logger.info('DOI redirected to a page of a known publisher: IntechOpen')

        chapter_id = re.search(r'/chapters/(\d+)', publisher_url).group(1)
        download_link = 'https://www.intechopen.com' + '/chapter/pdf-download/' + chapter_id

        download_link_meta = LinkMeta(download_link, guarantee=True)

    if doi.startswith('10.3390'):  # MDPI publisher
        logger.info('DOI redirected to a page of a known publisher: MDPI')

        download_link = publisher_url.rstrip('/') + '/pdf'

        download_link_meta = LinkMeta(download_link, guarantee=True)

    if download_link_meta == EmptyLinkMeta:
        download_link_meta = _analyze_generic_content(soup, publisher_url)

    return download_link_meta
