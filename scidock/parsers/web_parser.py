import json
import re

import requests
from bs4 import BeautifulSoup

from scidock.config import logger
from scidock.utils import filename_from_metadata, save_file_to_repo

__all__ = ('attempt_download',)


def attempt_download(doi: str, proxies: dict[str, str] | None = None) -> tuple[bool, str]:
    if proxies is None:
        proxies = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.3'}
    logger.info(f'Attempting to follow a DOI redirect with DOI = {doi} and proxy configuration: {proxies}')

    publisher_page = requests.get(f'https://doi.org/{doi}', proxies=proxies, headers=headers, timeout=5)
    soup = BeautifulSoup(publisher_page.text, 'html.parser')

    if publisher_page.headers.get('Content-Type') in ('application/pdf', 'application/octet-stream'):
        logger.info('DOI redirected to a page with plain PDF')
        title = soup.title.text
        filename = filename_from_metadata(doi, title)

        return save_file_to_repo(publisher_page.url, filename, doi, title, 'DOI redirect', proxies), publisher_page.url

    if doi.startswith('10.1109') or 'IEEE' in soup.title.text:  # IEEE publisher
        logger.info('DOI redirected to a page of a known publisher: IEEE')

        metadata_pattern = re.compile(r'xplGlobal.document.metadata=(.*?});', re.MULTILINE | re.DOTALL)
        script = soup.find('script', string=metadata_pattern)
        metadata = json.loads(metadata_pattern.search(script.string).group(1))

        download_link = 'https://ieeexplore.ieee.org' + metadata['pdfPath']
        download_link = download_link.replace('iel', 'ielx')  # might be unstable
        title = metadata['displayDocTitle']
        filename = filename_from_metadata(doi, title)

        return save_file_to_repo(download_link, filename, doi, title, 'IEEE', proxies), download_link

    if doi.startswith('10.5772') or 'intechopen' in soup.title.text:  # IntechOpen publisher
        logger.info('DOI redirected to a page of a known publisher: IntechOpen')

        chapter_id = re.search(r'/chapters/(\d+)', publisher_page.url).group(1)
        download_link = 'https://www.intechopen.com' + '/chapter/pdf-download/' + chapter_id
        title = soup.find('h1', class_='title').text
        filename = filename_from_metadata(doi, title)

        return save_file_to_repo(download_link, filename, doi, title, 'IntechOpen', proxies), download_link

    if doi.startswith('10.3390') or 'mdpi' in soup.title.text:  # MDPI publisher
        logger.info('DOI redirected to a page of a known publisher: MDPI')

        download_link = publisher_page.url.rstrip('/') + '/pdf'
        title = soup.find('h1', class_='title').text
        filename = filename_from_metadata(doi, title)

        return save_file_to_repo(download_link, filename, doi, title, 'MDPI', proxies), download_link

    download_text_match = soup.find(string=re.compile(r'\bdownload\b', re.IGNORECASE))
    pdf_text_match = soup.find(string=re.compile('PDF', re.IGNORECASE))
    if download_text_match is not None or pdf_text_match is not None:
        return False, publisher_page.url

    return False, ''
