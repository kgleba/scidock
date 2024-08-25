import re
import string
from dataclasses import dataclass

__all__ = ('SearchResult',)


@dataclass
class SearchResult:
    title: str
    DOI: str
    authors: list[str]
    download_link: str
    link_guarantee: bool
    abstract: str = ''

    def __str__(self):
        if self.link_guarantee:
            certainty_emoji = chr(9745) + ' '  # '☑️' but aligned correctly
        elif self.download_link:
            certainty_emoji = '🔎'
        else:
            certainty_emoji = '❌'

        return f"{certainty_emoji} {self.title.rstrip('.')}. DOI: {self.DOI}"

    @property
    def filename(self):
        title = self.title.strip()
        remove_punctuation = str.maketrans('', '', string.punctuation)
        filename = title.translate(remove_punctuation).replace(' ', '_')

        filename = re.sub('_+', '_', filename)
        filename = re.sub('[\r\n]', '', filename)

        return '.'.join((self.DOI, filename, 'pdf')).replace('/', '.')
