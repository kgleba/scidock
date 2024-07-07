import platform
import re
import subprocess
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from ipaddress import IPv4Address, IPv6Address
from itertools import chain
from pathlib import Path
from pprint import pformat

import click
import questionary
from click_params import IP_ADDRESS
from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process

from scidock.config import logger
from scidock.parsers.web_parser import attempt_download
from scidock.search_engines import arxiv_engine as arxiv
from scidock.search_engines import crossref_engine as crossref
from scidock.search_engines import scihub_engine as scihub
from scidock.search_engines.metadata import Metadata
from scidock.ui import progress_bar
from scidock.utils import (
    dump_json,
    get_current_proxy_setting,
    get_default_repository_path,
    load_json,
    random_chain,
    remove_outdated_repos,
    require_initialized_repository,
)

FUZZY_MATCH_RATE = 75


def update_recent_searches(paper: str):
    split_location = re.search(r'\. DOI: ', paper)
    title, doi = paper[:split_location.start()], paper[split_location.end():]

    repository_path = get_default_repository_path()
    content_path = f'{repository_path}/.scidock/content.json'

    repository_content = load_json(content_path)
    repository_content['recent_searches'][title] = asdict(Metadata(title, doi))
    dump_json(repository_content, content_path)


def precalculate_lazy_iterator(iterator: Iterator) -> Iterator:
    first_element = next(iterator, None)
    if first_element is None:
        return iterator
    return chain((first_element,), iterator)


def split_search_results(query: str, arxiv_results: Iterator, search_results: Iterator) -> tuple[list, Iterator]:
    # approach of defining the cutoff value for CrossRef relevance scores
    search_prefix = []
    prefix_score_ratios = []
    prefix_max = -1
    previous_score = 0

    progress_bar.update('Searching the CrossRef database...')

    arxiv_ids = arxiv.extract_arxiv_ids(query)

    if arxiv_ids:
        search_prefix += list(map(str, arxiv_results))

    with ThreadPoolExecutor() as pool:
        arxiv_future = pool.submit(precalculate_lazy_iterator, arxiv_results)
        search_future = pool.submit(precalculate_lazy_iterator, search_results)

        arxiv_results = arxiv_future.result()
        progress_bar.update('Searching through the arXiv preprints...')
        search_results = search_future.result()

    for search_result in search_results:
        search_prefix.append(str(search_result))

        prefix_max = max(prefix_max, search_result.relevance_score)
        prefix_score_ratios.append((search_result.relevance_score - previous_score) / prefix_max)
        if len(search_prefix) >= 8:  # noqa: PLR2004 - arbitrary number, should be tweaked afterwards
            best_score_ratio = prefix_score_ratios.index(max(prefix_score_ratios[1:]))
            insert_point = best_score_ratio + 2
            search_prefix.insert(insert_point, questionary.Separator())
            search_prefix[insert_point:insert_point] = [str(next(arxiv_results, '')) for _ in range(5)]
            search_prefix = list(filter(lambda result: result, search_prefix))

            break

    search_results = random_chain(search_results, arxiv_results, weights=[0.4, 0.6])

    return search_prefix, search_results


@click.group()
def main():
    pass


@click.group()
def config():
    pass


# TODO: create `scidock test proxy`

@config.command('proxy')
@click.argument('proxy_type', type=click.Choice(['http', 'socks5'], case_sensitive=False))
@click.argument('ip', type=IP_ADDRESS)
@click.argument('port', type=int)
def proxy_configuration(proxy_type: str, ip: IPv4Address | IPv6Address, port: int):
    scidock_root = Path('~/.scidock').expanduser()
    current_config = load_json(scidock_root / 'config.json')
    current_config['proxy'] = {'type': proxy_type, 'ip': str(ip), 'port': port}
    dump_json(current_config, scidock_root / 'config.json')

    click.echo('Successfully configured proxy!')


def init(repository_path: Path, name: str | None = None):
    scidock_root = Path('~/.scidock').expanduser()
    scidock_repo_root = repository_path / '.scidock'
    if Path(scidock_repo_root).exists():
        click.echo('Repository in this directory is already initialized!', err=True)
        return

    scidock_root.mkdir(exist_ok=True)

    current_config = load_json(scidock_root / 'config.json')

    if current_config.get('repositories') is None:
        current_config['repositories'] = {}

    current_config['repositories'] = remove_outdated_repos(current_config['repositories'])

    scidock_repo_root.mkdir(parents=True)

    if name is not None:
        new_repository_name = name
    else:
        parts_included = 1
        new_repository_name = repository_path.absolute().parts[-1]
        while new_repository_name in current_config['repositories']:
            parts_included += 1
            new_repository_name = '/'.join(repository_path.parts[-parts_included:])

    new_repository_repr = {new_repository_name: {'path': str(repository_path.absolute())}}
    current_config['repositories'].update(new_repository_repr)
    current_config['default'] = new_repository_name
    current_config['proxy'] = {}

    dump_json({'local': {}, 'recent_searches': {}}, scidock_repo_root / 'content.json')
    dump_json(current_config, scidock_root / 'config.json')

    logger.info(f'Initialized repository with the following setup: {pformat(current_config)}')
    click.echo('Successfully initialized the repository!')


def download(query: str, proxies: dict[str, str] | None) -> bool:
    logger.info(f'Received download request with {query = }')

    query_dois = crossref.extract_dois(query)
    if len(query_dois) != 1:
        raise click.BadParameter('Target DOI is either not specified or ambiguous')

    progress_bar.start()
    progress_bar.update('Searching for a downloadable copy of the chosen paper...')

    target_doi = query_dois[0]

    target_arxiv_ids = arxiv.extract_arxiv_ids(target_doi, allow_overlap=True, strict=True)
    if target_arxiv_ids:
        arxiv.download(target_arxiv_ids[0])
        progress_bar.stop()
        click.echo('Successfully downloaded the paper!')
        return True

    if scihub.download(target_doi, proxies):
        progress_bar.stop()
        click.echo('Successfully downloaded the paper!')
        return True

    attempt_success, recommended_url = attempt_download(target_doi, proxies)
    if attempt_success:
        progress_bar.stop()
        click.echo('Successfully downloaded the paper!')
        return True

    progress_bar.stop()
    click.echo('A downloadable version of this work could not be found automatically :(')

    if recommended_url:
        click.echo(f'However, you could try and download the paper from the publisher\'s website manually: {recommended_url}')

    return False


def search(query: str, proxy: bool, extended: bool, not_interactive: bool):
    # Suggested Workflow
    # Users get suggestions based on the relevance score provided by CrossRef
    # They are also provided with the option to open a pager (like GNU less) and scroll through more data generated on the fly
    # If nothing is to their liking, we can proceed searching for preprints in arXiv or in Google Scholar
    # The final goal of the search process is to retrieve the DOI, then one can proceed to the download stage

    proxies = {}
    if proxy:
        proxies = get_current_proxy_setting()

    progress_bar.start()

    search_results = crossref.search(query)

    arxiv_results = arxiv.search(query, extended)
    search_prefix, search_results = split_search_results(query, arxiv_results, search_results)

    progress_bar.stop()

    desired_paper = None
    try:
        if not not_interactive:
            # noinspection PyTypeChecker
            # signature changes at a runtime, see `ui.IterativeInquirerControl`
            desired_paper = questionary.select(message='Choose the suitable paper to add to your library',
                                               choices=(search_prefix, search_results),
                                               pointer='\u276f').ask()
    except ValueError as e:
        if str(e) == 'No choices provided':
            click.echo('Nothing found! :(')
        return

    if desired_paper is not None:
        download_status = download(desired_paper, proxies)

        if not download_status:
            update_recent_searches(desired_paper)


def open_pdf(query: str):
    repository_path = get_default_repository_path()
    repository_content = load_json(f'{repository_path}/.scidock/content.json')

    query_dois = crossref.extract_dois(query)
    query_arxiv_ids = arxiv.extract_arxiv_ids(query)
    query_ids = query_dois + query_arxiv_ids
    if len(query_ids) > 1:
        raise click.BadParameter('Specified too many IDs: impossible to open single paper')

    filenames = list(repository_content['local'].keys())
    titles = [entry['title'] for entry in repository_content['local'].values()]
    dois = [entry['DOI'] for entry in repository_content['local'].values()]

    # noinspection PyTypeChecker
    # authors of the `rapidfuzz` library incorrectly specified the signature of the function
    best_title_match = process.extractOne(query, titles, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_RATE,
                                          processor=default_process)

    best_id_match = None
    if query_ids:
        # noinspection PyTypeChecker
        best_id_match = process.extractOne(query_ids[0], dois, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_RATE,
                                           processor=default_process)

    if best_title_match is None and best_id_match is None:
        click.echo('Did not find any relevant papers :(')
        return

    best_match = best_id_match if best_id_match is not None else best_title_match

    best_match_filename = filenames[best_match[2]]
    best_match_path = f'{repository_path}/{best_match_filename}'
    if ' ' in best_match_path:
        best_match_path = f'"{best_match_path}"'

    logger.info(f'Best Match Relevance Score: {best_match[1]}')

    # TODO: verify PDF header (to exclude the possibility of arbitrary code execution)
    # TODO: implement resolving full binary paths

    match platform.system():
        case 'Windows':
            subprocess.run(['powershell', '-Command', 'Invoke-Item', best_match_path], check=False)  # noqa: S603, S607 - see TODOs above
        case 'Linux':
            subprocess.run(['xdg-open', best_match_path], check=False)  # noqa: S603, S607 - see TODOs above
        case 'Darwin':
            subprocess.run(['open', best_match_path], check=False)  # noqa: S603, S607 - see TODOs above
        case _:
            logger.error(f'Operating system "{platform.system()}" not recognized!')
            return

    click.echo('Successfully opened the file!')


@click.command('init')
@click.argument('repository_path', type=click.Path(file_okay=False, path_type=Path))
@click.option('--name', type=str, default=None, help='Name of the repository. Defaults to the name of the folder')
def init_command(repository_path: Path, name: str | None):
    init(repository_path, name)


@click.command('search')
@click.argument('query', type=str)
@click.option('--proxy', is_flag=True, default=False, help='Whether to use a proxy in subsequent download requests')
@click.option('--extended', is_flag=True, default=False,
              help='Whether to include abstract and other fields in the search. Defaults to False (search by title only)')
@click.option('-n', '--not-interactive', is_flag=True, default=False, hidden=True,
              help='Disable user interactions (for CI/CD use only)')
@require_initialized_repository
def search_command(query: str, proxy: bool, extended: bool, not_interactive: bool):
    search(query, proxy, extended, not_interactive)


@click.command('download')
@click.argument('DOI', type=str)
@click.option('--proxy', is_flag=True, default=False, help='Whether to use a proxy in download requests')
@require_initialized_repository
def download_command(doi: str, proxy: bool):
    proxies = {}
    if proxy:
        proxies = get_current_proxy_setting()

    download(doi, proxies)


@click.command('open')
@click.argument('query', type=str)
@require_initialized_repository
def open_command(query: str):
    open_pdf(query)


main.add_command(init_command)
main.add_command(search_command)
main.add_command(download_command)
main.add_command(open_command)

main.add_command(config)

if __name__ == '__main__':
    main()
