import re
from dataclasses import dataclass
from enum import Enum, auto

from bs4 import BeautifulSoup

__all__ = ('PatternStatus', 'Standalone', 'DominantPair')


class PatternStatus(Enum):
    POSITIVE = auto()
    NEUTRAL = auto()
    NEGATIVE = auto()
    NOT_TRIGGERED = auto()


@dataclass
class Standalone:
    pattern: str | re.Pattern
    on_trigger: PatternStatus

    def __post_init__(self):
        if isinstance(self.pattern, str):
            self.pattern = re.compile(self.pattern, flags=re.IGNORECASE)

    def status(self, soup: BeautifulSoup) -> PatternStatus:
        if soup.find(string=self.pattern):
            return self.on_trigger

        return PatternStatus.NOT_TRIGGERED

    def __str__(self):
        return f'Standalone(pattern={self.pattern.pattern!r}, on_trigger={self.on_trigger.name})'

    def __hash__(self):
        return hash(str(self))


@dataclass
class DominantPair:
    leader: Standalone
    follower: Standalone

    def status(self, soup: BeautifulSoup) -> PatternStatus:
        leader_status = self.leader.status(soup)
        follower_status = self.follower.status(soup)

        if leader_status != PatternStatus.NOT_TRIGGERED:
            return leader_status

        return follower_status

    def __str__(self):
        return f'DominantPair(leader={self.leader}, follower={self.follower})'

    def __hash__(self):
        return hash(str(self))
