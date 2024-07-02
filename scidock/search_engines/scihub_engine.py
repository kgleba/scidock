import string

import requests
from bs4 import BeautifulSoup

from scidock.config import logger
from scidock.utils import save_file_to_repo

# TODO: make mirrors dynamic or more configurable
SCIHUB_MIRRORS = ['https://sci-hub.ru', 'https://sci-hub.se', 'https://sci-hub.st']
SCIDB_MIRRORS = ['https://annas-archive.gs/scidb', 'https://annas-archive.se/scidb']


def download(doi: str, proxies: dict[str, str] | None = None) -> bool:
    if proxies is None:
        proxies = {}
    logger.info(f'Attempting to download a file with DOI = {doi} and proxy configuration: {proxies}')

    for mirror in SCIHUB_MIRRORS:
        try:
            # TODO: choose a sensible timeout based on the Internet speed
            timeout = 5 if proxies else 2
            preview_page = requests.get(f'{mirror}/{doi}', proxies=proxies, timeout=timeout)
            break
        except requests.exceptions.Timeout:
            logger.debug(f'Timeout for the {mirror} Sci-Hub mirror')
            continue
    else:
        print('Unfortunately, all of the Sci-Hub mirrors are unavailable at your location. Try using a proxy')
        return False

    soup = BeautifulSoup(preview_page.text, 'html.parser')

    download_button = soup.find('button')
    if not download_button:
        logger.info('Did not find the download button')
        return False

    if download_button.get('onclick') is None:
        logger.error('Download button does not have an "onclick" attribute (website DOM structure has changed)!')
        return False

    redirect_code = download_button['onclick']
    redirect_location = redirect_code.removeprefix("location.href='").removesuffix("'")
    download_link = ('https:' if redirect_location.startswith('//') else mirror) + redirect_location

    # TODO: improve citation parsing
    citation_container = soup.find('div', id='citation')
    citation_italic = citation_container.findChild('i')
    citation_title = citation_italic.text if citation_italic is not None else citation_container.text

    remove_punctuation = str.maketrans('', '', string.punctuation)
    filename = citation_title.translate(remove_punctuation).replace(' ', '_')
    filename = '.'.join((doi.replace('/', '.'), filename, 'pdf'))

    return save_file_to_repo(download_link, filename, doi, citation_title, 'Sci-Hub', proxies)
