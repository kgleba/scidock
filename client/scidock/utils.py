import re
import sys
from os import PathLike
from pathlib import Path
from typing import Any

import orjson
from questionary import Choice

from scidock.meta import SearchResult

__all__ = (
    'extract_dois',
    'extract_arxiv_ids',
    'load_json',
    'dump_json',
    'global_config_exists',
    'raw_result_to_choice',
)

DOI_PATTERN = re.compile(r'10.\d{4,9}/[-._;()/:a-zA-Z0-9]+')
ARXIV_PATTERN = re.compile(r'(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?')


def extract_dois(query: str) -> list[str]:
    return DOI_PATTERN.findall(query)


def extract_arxiv_ids(query: str) -> list[str]:
    return [''.join(match) for match in ARXIV_PATTERN.findall(query)]


def load_json(filename: str | PathLike) -> Any:
    try:
        file_content = Path(filename).expanduser().read_bytes()
        data = orjson.loads(file_content)
    except (orjson.JSONDecodeError, FileNotFoundError):
        data = {}
    return data


def dump_json(data: Any, filename: str | PathLike) -> None:
    data_representation = orjson.dumps(data, option=orjson.OPT_INDENT_2)
    Path(filename).expanduser().write_bytes(data_representation)


def global_config_exists() -> bool:
    global_config_path = Path('~/.scidock/config.json').expanduser()
    return global_config_path.exists()


def emergency_exit() -> None:
    Path('~/.scidock/config.json').expanduser().unlink()
    sys.exit(1)


def raw_result_to_choice(raw_result: dict) -> Choice:
    result = SearchResult(**raw_result)
    return Choice(str(result), result)
