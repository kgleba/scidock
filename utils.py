import json
from os import PathLike
from pathlib import Path
from typing import Any
from functools import cache


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


def remove_outdated_repos(repositories: dict) -> dict:
    up_to_date_repositories = {}

    for repository_name, repository in repositories.items():
        if Path(repository['path']).exists():
            up_to_date_repositories[repository_name] = repository

    return up_to_date_repositories


def responsive_cache(func):
    func = cache(func)

    def format_args(args) -> str:
        return ', '.join(map(repr, args))

    def format_kwargs(kwargs) -> str:
        return ', '.join(f'{k}={repr(v)}' for k, v in kwargs.items())

    def notification_wrapper(*args, **kwargs):
        hits = func.cache_info().hits
        func_return = func(*args, **kwargs)
        func_args = ', '.join((format_args(args), format_kwargs(kwargs)))

        print(f'Cache for {func.__name__}({func_args}) {'hit' if func.cache_info().hits > hits else 'missed'}')

        return func_return

    return notification_wrapper
