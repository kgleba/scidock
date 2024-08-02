from dataclasses import dataclass

__all__ = ('SearchMeta', 'LinkMeta', 'EmptySearchMeta', 'EmptyLinkMeta', 'merge_result_link')


@dataclass
class SearchMeta:
    title: str
    DOI: str
    authors: list[str]
    abstract: str

    download_link: str = ''
    relevance_score: float = 1000.0


@dataclass
class LinkMeta:
    link: str
    guarantee: bool


def merge_result_link(result: SearchMeta, link: LinkMeta, include_abstract: bool) -> dict:
    search_result = {'title': result.title, 'DOI': result.DOI, 'authors': result.authors,
                     'download_link': link.link, 'link_guarantee': link.guarantee}

    if include_abstract:
        return search_result | {'abstract': result.abstract}

    return search_result


EmptySearchMeta = SearchMeta('UNTITLED', '', [], '')
EmptyLinkMeta = LinkMeta('', False)
