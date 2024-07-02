import json
import random
from dataclasses import asdict
from functools import cache, wraps
from ipaddress import IPv4Address, IPv6Address
from os import PathLike
from pathlib import Path
from typing import Any

import requests

from scidock.config import logger
from scidock.search_engines.metadata import Metadata

KB = 1024


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


def is_repository_initialized() -> bool:
    scidock_root = Path('~/.scidock').expanduser()

    if not (scidock_root / 'config.json').exists():
        return False

    repositories = load_json(scidock_root / 'config.json')
    return repositories.get('default') is not None


def require_initialized_repository(func):
    @wraps(func)
    def init_wrapper(*args, **kwargs):
        if not is_repository_initialized():
            logger.error('At least one repository should be initialized! See `scidock init --help`')
            return None

        return func(*args, **kwargs)

    return init_wrapper


def remove_outdated_repos(repositories: dict) -> dict:
    up_to_date_repositories = {}

    for repository_name, repository in repositories.items():
        if Path(repository['path']).exists():
            up_to_date_repositories[repository_name] = repository

    return up_to_date_repositories


def save_file_to_repo(download_link: str, filename: str, doi: str, title: str, caller_id: str,
                      proxies: dict[str, str] | None = None) -> bool:
    if proxies is None:
        proxies = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.3'}

    logger.info(f'Attempting to download a file from {caller_id} with {filename = } and {download_link = } for {doi = }')

    repository_path = get_default_repository_path()
    download_page = requests.get(download_link, proxies=proxies, stream=True, headers=headers, timeout=10)

    if download_page.status_code != 200:  # noqa: PLR2004 - the meaning and purpose of (status code) 200 are obvious from the context
        logger.info(f'Download failed with {download_page.status_code = }')
        return False

    if download_page.headers.get('Content-Type') != 'application/pdf':
        logger.info('Download failed as Content-Type of the page is not "application/pdf"')
        return False

    with open(f'{repository_path}/{filename}', 'wb') as paper_file:
        for chunk in download_page.iter_content(chunk_size=10 * KB):
            paper_file.write(chunk)

    content_path = f'{repository_path}/.scidock/content.json'
    repository_content = load_json(content_path)
    repository_content['local'][filename] = asdict(Metadata(title, doi))
    dump_json(repository_content, content_path)

    return True


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

    @wraps(func)
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
