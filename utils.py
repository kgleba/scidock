import json
from os import PathLike
from typing import Any


def load_json(filename: str | PathLike) -> Any:
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        data = {}
    return data


def dump_json(data: Any, filename: str | PathLike) -> None:
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False)
