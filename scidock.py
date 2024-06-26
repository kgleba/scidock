import platform
import subprocess
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path

import click
import questionary
from click_params import IP_ADDRESS
from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process

from search_engines import arxiv_engine as arxiv
from search_engines import crossref_engine as crossref
from search_engines import scihub_engine as scihub
from ui import progress_bar
from utils import dump_json, get_current_proxy_setting, get_default_repository_path, load_json, random_chain, remove_outdated_repos

FUZZY_MATCH_RATE = 60


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


def init(repository_path: Path, name: str | None):
    scidock_root = Path('~/.scidock').expanduser()
    scidock_repo_root = repository_path / '.scidock'
    if Path(scidock_repo_root).exists():
        click.echo('Repository in this directory is already initialized!', err=True)
        return

    scidock_repo_root.mkdir(parents=True)
    scidock_root.mkdir(exist_ok=True)

    current_config = load_json(scidock_root / 'config.json')

    if current_config.get('repositories') is None:
        current_config['repositories'] = {}

    current_config['repositories'] = remove_outdated_repos(current_config['repositories'])

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

    dump_json({}, scidock_repo_root / 'content.json')
    dump_json(current_config, scidock_root / 'config.json')

    click.echo('Successfully initialized the repository!')


def download(query: str, proxies: dict[str, str] | None = None):
    query_dois = crossref.extract_dois(query)
    if len(query_dois) != 1:
        raise click.BadParameter('Target DOI is either not specified or ambiguous')

    target_doi = query_dois[0]

    target_arxiv_ids = arxiv.extract_arxiv_ids_strictly(target_doi)
    if target_arxiv_ids:
        arxiv.download(target_arxiv_ids[0])
        click.echo('Successfully downloaded the paper!')
        return

    if scihub.download(target_doi, proxies):
        click.echo('Successfully downloaded the paper!')
        return

    click.echo('A downloadable version of this work could not be found :(')


def search(query: str, proxy: bool):
    # Suggested Workflow
    # Users get suggestions based on the relevance score provided by CrossRef
    # They are also provided with the option to open a pager (like GNU less) and scroll through more data generated on the fly
    # If nothing is to their liking, we can proceed searching for preprints in arXiv or in Google Scholar
    # The final goal of the search process is to retrieve the DOI, then one can proceed to the download stage

    proxies = {}
    if proxy:
        proxies = get_current_proxy_setting()

    progress_bar.start()

    # approach of defining the cutoff value for CrossRef relevance scores
    search_prefix = []
    prefix_score_ratios = []
    prefix_max = -1
    previous_score = 0

    progress_bar.update('Searching the CrossRef database...')

    n_search_results, search_results = crossref.search(query)

    if n_search_results > 10_000:  # noqa: PLR2004 - arbitrary number, should be tweaked afterwards
        progress_bar.stop()

        refine_query = questionary.confirm(
            f'There are more than {n_search_results:,} search results. Do you want to make your query more specific?').ask()
        if refine_query:
            return

        progress_bar.start()

    progress_bar.update('Searching through the arXiv preprints...')

    arxiv_ids = arxiv.extract_arxiv_ids(query)
    arxiv_results = arxiv.search(query)
    if arxiv_ids:
        search_prefix += list(map(str, arxiv_results))
    arxiv_results = iter(arxiv_results)
    first_arxiv_result = str(next(arxiv_results, ''))

    # TODO: prefer downloadable options of the same paper

    for search_result in search_results:
        search_prefix.append(str(search_result))

        prefix_max = max(prefix_max, search_result.relevance_score)
        prefix_score_ratios.append((search_result.relevance_score - previous_score) / prefix_max)
        if len(search_prefix) >= 8:  # noqa: PLR2004 - arbitrary number, should be tweaked afterwards
            progress_bar.stop()

            best_score_ratio = prefix_score_ratios.index(max(prefix_score_ratios[1:]))
            insert_point = best_score_ratio + 2
            search_prefix.insert(insert_point, questionary.Separator())
            search_prefix[insert_point:insert_point] = [first_arxiv_result] + [str(next(arxiv_results, '')) for _ in range(4)]
            search_prefix = list(filter(lambda result: result, search_prefix))

            break

    search_results = random_chain(search_results, arxiv_results, weights=[0.4, 0.6])

    try:
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
        download(desired_paper, proxies)


def open_pdf(query: str):
    repository_path = get_default_repository_path()
    repository_content = load_json(f'{repository_path}/.scidock/content.json')

    filenames = list(repository_content.keys())
    metadata = [' '.join(entry.values()) for entry in repository_content.values()]

    # noinspection PyTypeChecker
    # authors of the `rapidfuzz` library incorrectly specified the signature of the function
    best_match = process.extractOne(query, metadata, scorer=fuzz.partial_token_ratio, score_cutoff=FUZZY_MATCH_RATE,
                                    processor=default_process)
    if best_match is None:
        click.echo('Did not find any relevant papers :(')
        return

    best_match_filename = filenames[best_match[2]]
    best_match_path = f'"{repository_path}/{best_match_filename}"'

    # TODO: log relevance score
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
            click.echo('Operating system not recognized!')
            return

    click.echo('Successfully opened the file!')


@click.command('init')
@click.argument('repository_path', type=click.Path(file_okay=False, path_type=Path))
@click.option('--name', type=str, help='Name of the repository. Defaults to the name of the folder')
def init_command(repository_path: Path, name: str | None):
    init(repository_path, name)


@click.command('search')
@click.argument('query', type=str)
@click.option('--proxy', is_flag=True, default=False, help='Whether to use a proxy in subsequent download requests')
def search_command(query: str, proxy: bool):
    search(query, proxy)


@click.command('download')
@click.argument('DOI', type=str)
@click.option('--proxy', is_flag=True, default=False, help='Whether to use a proxy in download requests')
def download_command(doi: str, proxy: bool):
    proxies = {}
    if proxy:
        proxies = get_current_proxy_setting()

    download(doi, proxies)


@click.command('open')
@click.argument('query', type=str)
def open_command(query: str):
    open_pdf(query)


main.add_command(init_command)
main.add_command(search_command)
main.add_command(download_command)
main.add_command(open_command)

main.add_command(config)

if __name__ == '__main__':
    main()
