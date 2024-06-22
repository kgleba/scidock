import json
import random
from functools import cache
from os import PathLike
from pathlib import Path
from typing import Any


def load_json(filename: str | PathLike) -> Any:
    try:
        with open(filename, encoding='utf-8') as file:
            data = json.load(file)
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        data = {}
    return data


def dump_json(data: Any, filename: str | PathLike) -> None:
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False)


def get_default_repository() -> str | None:
    scidock_root = Path('~/.scidock').expanduser()
    repositories = load_json(scidock_root / 'repositories.json')
    return repositories.get('default')


def remove_outdated_repos(repositories: dict) -> dict:
    up_to_date_repositories = {}

    for repository_name, repository in repositories.items():
        if Path(repository['path']).exists():
            up_to_date_repositories[repository_name] = repository

    return up_to_date_repositories


def random_chain(*iterables, weights: list[float] | None = None):
    iterators = [iter(it) for it in iterables]

    while iterators:
        iterator = random.choices(iterators, weights, k=1)[0]

        try:
            yield next(iterator)
        except StopIteration:
            iterator_index = iterators.index(iterator)

            iterators.pop(iterator_index)
            if weights is not None:
                weights.pop(iterator_index)


def responsive_cache(func):
    func = cache(func)

    def format_args(args) -> str:
        return ', '.join(map(repr, args))

    def format_kwargs(kwargs) -> str:
        return ', '.join(f'{k}={v!r}' for k, v in kwargs.items())

    def notification_wrapper(*args, **kwargs):
        hits = func.cache_info().hits
        func_return = func(*args, **kwargs)
        func_args = ', '.join((format_args(args), format_kwargs(kwargs)))

        print(f'Cache for {func.__name__}({func_args}) {'hit' if func.cache_info().hits > hits else 'missed'}')

        return func_return

    return notification_wrapper
