from collections.abc import Iterator  # noqa: I001 - local imports are grouped together
from dataclasses import asdict, dataclass

import arxiv

from utils import dump_json, get_default_repository_path, load_json
from .metadata import Metadata
from .query_parser import clear_query, extract_arxiv_ids, extract_arxiv_ids_strictly, extract_names

client = arxiv.Client()

__all__ = ('search', 'download', 'extract_arxiv_ids', 'extract_arxiv_ids_strictly')


@dataclass
class ArXivItem:
    title: str
    arxiv_id: str
    relevance_score: float = 1000.0

    def __post_init__(self):
        self.DOI = f'10.48550/arXiv.{self.arxiv_id}'

    def __str__(self):
        return f'{self.title.rstrip('.')}. DOI: {self.DOI}'


def search(query: str) -> Iterator[ArXivItem]:
    arxiv_ids = extract_arxiv_ids(query)

    if arxiv_ids:
        search_request = arxiv.Search(id_list=arxiv_ids)
        for paper in client.results(search_request):
            yield ArXivItem(paper.title, paper.get_short_id())

        return

    search_query = ''

    names = extract_names(query)
    if names is not None:
        search_query += 'au:' + ' AND '.join(names)

    # TODO: do something clever with extracting titles

    search_query += 'all:' + clear_query(query)
    search_request = arxiv.Search(query=search_query, sort_by=arxiv.SortCriterion.Relevance)

    for paper in client.results(search_request):
        yield ArXivItem(paper.title, paper.get_short_id())


def download(arxiv_id: str):
    search_request = arxiv.Search(id_list=[arxiv_id])
    paper = next(client.results(search_request))

    repository_path = get_default_repository_path()
    # noinspection PyProtectedMember
    filename = paper._get_default_filename()

    paper.download_pdf(dirpath=repository_path)

    content_path = f'{repository_path}/.scidock/content.json'
    repository_content = load_json(content_path)
    repository_content[filename] = asdict(Metadata(paper.title, f'10.48550/arXiv.{paper.get_short_id()}'))
    dump_json(repository_content, content_path)
