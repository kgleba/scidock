from dataclasses import dataclass

__all__ = ('Metadata',)


@dataclass
class Metadata:
    title: str
    DOI: str
