import requests
from bs4 import BeautifulSoup

from scidock.config import logger
from scidock.utils import filename_from_metadata, save_file_to_repo

# TODO: make mirrors dynamic or more configurable
SCIHUB_MIRRORS = ['https://sci-hub.ru', 'https://sci-hub.se', 'https://sci-hub.st']
SCIDB_MIRRORS = ['https://annas-archive.gs/scidb', 'https://annas-archive.se/scidb']


def parse_scihub(soup: BeautifulSoup, doi: str, mirror: str) -> tuple[str | None, str | None, str | None]:
    download_button = soup.find('button')
    if not download_button:
        logger.info('Did not find the download button')
        return None, None, None

    if download_button.get('onclick') is None:
        logger.error('Download button does not have an "onclick" attribute (Sci-Hub DOM structure has changed)!')
        return None, None, None

    redirect_code = download_button['onclick']
    redirect_location = redirect_code.removeprefix("location.href='").removesuffix("'")
    download_link = ('https:' if redirect_location.startswith('//') else mirror) + redirect_location

    # TODO: improve citation parsing
    citation_container = soup.find('div', id='citation')
    citation_italic = citation_container.findChild('i')
    citation_title = citation_italic.text if citation_italic is not None else citation_container.text

    filename = filename_from_metadata(doi, citation_title)

    return download_link, filename, citation_title


def parse_scidb(soup: BeautifulSoup, doi: str) -> tuple[str | None, str | None, str | None]:
    download_button = soup.find('a', text='Download')
    if not download_button:
        logger.info('Did not find the download button')
        return None, None, None

    download_link = download_button['href']
    title_container = soup.find('div', class_='font-bold')
    title = title_container.text.removesuffix('🔍').strip()
    filename = filename_from_metadata(doi, title)

    return download_link, filename, title


def download(doi: str, proxies: dict[str, str] | None = None) -> bool:
    if proxies is None:
        proxies = {}
    logger.info(f'Attempting to download a file with DOI = {doi} and proxy configuration: {proxies}')

    for mirror in SCIHUB_MIRRORS + SCIDB_MIRRORS:
        try:
            # TODO: choose a sensible timeout based on the Internet speed
            timeout = 5 if proxies else 2
            preview_page = requests.get(f'{mirror}/{doi}', proxies=proxies, timeout=timeout, allow_redirects=False)
            break
        except requests.exceptions.Timeout:
            logger.debug(f'Timeout for the {mirror} Sci-Hub mirror')
            continue
    else:
        print('Unfortunately, all of the Sci-Hub mirrors are unavailable at your location. Try using a proxy')
        return False

    if preview_page.status_code in (301, 302):
        return False

    soup = BeautifulSoup(preview_page.text, 'html.parser')

    if 'sci-hub' in mirror:
        download_link, filename, title = parse_scihub(soup, doi, mirror)
        if any(field is None for field in (download_link, filename, title)):
            return False
    else:
        download_link, filename, title = parse_scidb(soup, doi)
        if any(field is None for field in (download_link, filename, title)):
            return False

    return save_file_to_repo(download_link, filename, doi, title, 'Sci-Hub', proxies)
