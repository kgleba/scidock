from collections.abc import Iterator
from dataclasses import asdict, dataclass

import arxiv

from scidock.config import logger
from scidock.parsers.query_parser import clear_query, extract_arxiv_ids, extract_names
from scidock.search_engines.metadata import Metadata
from scidock.utils import dump_json, get_default_repository_path, load_json

client = arxiv.Client()

__all__ = ('search', 'download', 'extract_arxiv_ids')


@dataclass
class ArXivItem:
    title: str
    arxiv_id: str
    relevance_score: float = 1000.0

    def __post_init__(self):
        self.DOI = f'10.48550/arXiv.{self.arxiv_id}'

    def __str__(self):
        return f'{self.title.rstrip(".")}. DOI: {self.DOI}'


def search(query: str, extended: bool = False) -> Iterator[ArXivItem]:
    arxiv_ids = extract_arxiv_ids(query)
    logger.info(f'Extracted arXiv IDs: {arxiv_ids!r}')

    if arxiv_ids:
        search_request = arxiv.Search(id_list=arxiv_ids)
        for paper in client.results(search_request):
            yield ArXivItem(paper.title, paper.get_short_id())

        return

    search_query = ''

    names = extract_names(query)
    logger.info(f'Extracted names: {names!r}')
    if names is not None:
        search_query += 'au:' + ' AND '.join(names)

    # TODO: do something clever with extracting titles

    search_query += ('all:' if extended else 'ti:') + clear_query(query)
    search_request = arxiv.Search(query=search_query, sort_by=arxiv.SortCriterion.Relevance)

    for paper in client.results(search_request):
        yield ArXivItem(paper.title, paper.get_short_id())


def download(arxiv_id: str):
    search_request = arxiv.Search(id_list=[arxiv_id])
    paper = next(client.results(search_request))

    repository_path = get_default_repository_path()
    # noinspection PyProtectedMember
    filename = paper._get_default_filename()
    logger.info(f'Attempting to download a file with {filename = } for {arxiv_id = }')

    paper.download_pdf(dirpath=repository_path)

    content_path = f'{repository_path}/.scidock/content.json'
    repository_content = load_json(content_path)
    repository_content['local'][filename] = asdict(Metadata(paper.title, f'10.48550/arXiv.{paper.get_short_id()}'))
    dump_json(repository_content, content_path)
