import re

import feedparser

from web.parsers.metadata import SearchMeta

ARXIV_PATTERN = r'(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})'
ARXIV_ID_PATTERN = re.compile(fr'http://arxiv.org/abs/({ARXIV_PATTERN})')

__all__ = ('extract_metadata', 'check_content_presence')


def check_content_presence(feed: str) -> bool:
    parsed_feed = feedparser.parse(feed)
    return bool(parsed_feed.entries)


def extract_metadata(feed: str) -> list[SearchMeta]:
    parsed_feed = feedparser.parse(feed)

    return [_extract_entry_metadata(entry) for entry in parsed_feed.entries]


def _extract_entry_metadata(entry: feedparser.FeedParserDict) -> SearchMeta:
    # https://github.com/lukasschwab/arxiv.py/issues/71
    title = entry.title if hasattr(entry, 'title') else '0'
    entry_id = ARXIV_ID_PATTERN.match(entry.id).group(1)

    authors = [author.name for author in entry.authors]

    download_link = ''
    for related_link in entry.links:
        if related_link.type == 'application/pdf':
            download_link = related_link.href
            break

    return SearchMeta(title=title,
                      DOI=f'10.48550/arXiv.{entry_id}',
                      authors=authors,
                      abstract=entry.summary,
                      download_link=download_link)
