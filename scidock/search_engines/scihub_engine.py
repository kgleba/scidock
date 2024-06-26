import string
from dataclasses import asdict

import requests
from bs4 import BeautifulSoup

from scidock.config import logger
from scidock.search_engines.metadata import Metadata
from scidock.utils import dump_json, get_default_repository_path, load_json

# TODO: make mirrors dynamic or more configurable
SCIHUB_MIRRORS = ['https://sci-hub.ru', 'https://sci-hub.se', 'https://sci-hub.st']

KB = 1024


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

    citation_title = soup.find('div', id='citation').findChild('i').text
    remove_punctuation = str.maketrans('', '', string.punctuation)  # remove punctuation
    filename = citation_title.translate(remove_punctuation).replace(' ', '_')
    filename = '.'.join((doi.replace('/', '.'), filename, 'pdf'))

    logger.info(f'Attempting to download a file with {filename = } and {download_link = } for {doi = }')

    repository_path = get_default_repository_path()
    downloaded_file = requests.get(download_link, proxies=proxies, stream=True, timeout=10)
    with open(f'{repository_path}/{filename}', 'wb') as paper_file:
        for chunk in downloaded_file.iter_content(chunk_size=10 * KB):
            paper_file.write(chunk)

    content_path = f'{repository_path}/.scidock/content.json'
    repository_content = load_json(content_path)
    repository_content[filename] = asdict(Metadata(citation_title, doi))
    dump_json(repository_content, content_path)

    return True
