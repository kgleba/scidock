import json
import random
from functools import cache
from ipaddress import IPv4Address, IPv6Address
from os import PathLike
from pathlib import Path
from typing import Any

from config import logger


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


def get_default_repository_path() -> str | None:
    scidock_root = Path('~/.scidock').expanduser()
    repositories = load_json(scidock_root / 'config.json')

    if repositories.get('default') is not None:
        return repositories['repositories'][repositories['default']]['path']

    return None


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

        logger.debug(f'Cache for {func.__name__}({func_args}) {'hit' if func.cache_info().hits > hits else 'missed'}')

        return func_return

    return notification_wrapper


def format_requests_proxy(proxy_type: str, ip: IPv4Address | IPv6Address, port: int):
    connection_string = f'{proxy_type}://{ip}:{port}'
    return {'http': connection_string, 'https': connection_string}


def get_current_proxy_setting():
    scidock_root = Path('~/.scidock').expanduser()
    current_config = load_json(scidock_root / 'config.json')
    return format_requests_proxy(*current_config['proxy'].values())

# TODO: consider creating context managers for working with different config files
