import platform
import subprocess
from http import HTTPStatus
from pathlib import Path
from threading import Thread

import click
import httpx
import orjson
import questionary
import validators
from fake_useragent import UserAgent
from httpx_sse import connect_sse
from questionary import ValidationError, Validator
from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process
from rich.status import Status

from scidock import interface
from scidock.config import global_config, repo_config
from scidock.log import logger
from scidock.meta import SearchResult
from scidock.utils import (
    extract_arxiv_ids,
    extract_dois,
    global_config_exists,
    raw_result_to_choice,
)

DIVIDING_LINE_BOUNDARY = 5
FUZZY_MATCH_RATE = 75
NOTHING_FOUND_STR = 'Nothing found! :('
SEARCH_RESULTS = []

UA = UserAgent()

progress_bar = Status('Parsing your query using AI...', spinner='dots2')

interface.patch_inquirer_control()


class URLValidator(Validator):
    def validate(self, document):
        if not validators.url(document.text):
            raise ValidationError(message='Enter valid URL', cursor_position=len(document.text))


def repository_short_name(repository_path: Path) -> str:
    repository_name = repository_path.absolute().parts[-1]

    parts_included = 1
    while repository_name in global_config.repositories:
        parts_included += 1
        repository_name = '/'.join(repository_path.parts[-parts_included:])

    return repository_name


def accumulate_search_results(
    query: str,
    extended: bool = False,
    attempt_download: bool = True,
    include_abstract: bool = False,
) -> None:
    global SEARCH_RESULTS  # noqa: PLW0603
    # TODO: it is important to find a better way though

    request_params = {
        'query': query,
        'extended': extended,
        'attempt_download': attempt_download,
        'include_abstract': include_abstract,
    }

    with httpx.Client(timeout=None) as client:  # noqa: SIM117, S113
        with connect_sse(
            client, 'GET', f'{global_config.server_url}/search', params=request_params
        ) as event_source:
            for sse in event_source.iter_sse():
                data_choices = map(raw_result_to_choice, orjson.loads(sse.data))
                SEARCH_RESULTS.extend(data_choices)

    if not SEARCH_RESULTS:
        SEARCH_RESULTS = [NOTHING_FOUND_STR]


def _open_pdf(path: str) -> None:
    # TODO: verify PDF header (to exclude the possibility of arbitrary code execution)
    # TODO: implement resolving full binary paths

    match platform.system():
        case 'Windows':
            subprocess.run(  # noqa: S603 - see TODOs above
                ['powershell', '-Command', 'Invoke-Item', path],  # noqa: S607 - see TODOs above
                check=False,
            )
        case 'Linux':
            subprocess.run(['xdg-open', path], check=False)  # noqa: S603, S607 - see TODOs above
        case 'Darwin':
            subprocess.run(['open', path], check=False)  # noqa: S603, S607 - see TODOs above
        case _:
            logger.error(f'Operating system "{platform.system()}" not recognized!')
            return

    click.echo('Successfully opened the file!')


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context):
    if not global_config_exists():
        tutorial()

        if ctx.invoked_subcommand:
            click.echo('\nAnd now for something completely different...\n')


def tutorial() -> None:
    questionary.print(
        'Hey there! Welcome to SciDock.\nIn this quick tutorial we will cover all the settings'
        ' and introduce you to the key features!'
    )
    questionary.print(
        "First of all, you should've created (or at least gotten a link to) a SciDock server.\n"
        "If you haven't, you can always read how in the docs: ...\n"
    )  # TODO: paste an actual link to the docs

    server_url = questionary.text(
        message='Enter the URL of your SciDock server: ', validate=URLValidator
    ).ask()
    global_config.server_url = server_url

    questionary.print(
        '\nThen we need to initialize your first repository.\n'
        'You will have to follow these steps every time you want to initialize a repository.\n'
        'However, you can skip the interactive part by passing the path directly as an argument:\n'
        '`scidock init /path/to/your/repo`\n'
    )
    init()

    questionary.print('')
    proxy_setup = questionary.confirm(
        message='Would you like to set up a proxy?', default=False
    ).ask()
    if proxy_setup:
        proxy = questionary.text(
            message='Enter the URL of your proxy: ', validate=URLValidator
        ).ask()

        global_config.proxy = proxy

    scidock_root = Path('~/.scidock').expanduser()
    scidock_root.mkdir(exist_ok=True)

    global_config.dump()

    questionary.print(
        "\n🚀 Congratulations! You're all set now.\n\n"
        '🔍 Try searching with `scidock search`!\n'
        "For example, run `scidock search 'deep learning'`\n"
        'Notice that AI processes your query, extracting key details to deliver highly relevant results.\n\n'
        "🎯 To refine your search, add specifics like an author's name: `scidock search 'deep learning by Guillaume Lample'`\n"
        'Unlike other search tools, SciDock adapts automatically and intelligently – no complex syntax needed!\n\n'  # noqa: RUF001
        'Each result comes with one of three emojis:\n'
        '☑️: The paper is ready for download\n'
        '🔎: A promising lead for further exploration\n'
        '❌: Added to your wishlist for future hunts\n\n'
        "You'll also notice a dividing line in the search results.\n"
        "Papers above the line are the most relevant to your query, helping you focus on what's most useful right away.\n\n"
        "💡 For the best results, use keywords from the paper's title or terms that clearly reflect the main content.\n"
        'While broad searches can be a good start, remember that specificity is key.\n\n'
        "📚 To open papers you've saved locally in your repo, use `scidock open`.\n"
        'You can still use free-form queries, so apply the same best practices when searching through files!\n\n'
        '🔬 If you need a refresher, you can always revisit this tutorial with the `scidock tutorial` command.\n\n'
        'SciDock is here to supercharge your research. Happy discovering!'
    )


def init(repository_path: Path | None = None) -> None:
    if repository_path is None:
        repository_path = Path(
            questionary.path(message='Enter the path to your repository: ').ask()
        ).expanduser()

    scidock_repo_root = Path(repository_path) / '.scidock'
    if scidock_repo_root.exists():
        click.echo('Repository in this directory is already initialized!', err=True)
        return

    scidock_repo_root.mkdir(parents=True)

    repository_name = repository_short_name(repository_path)
    repository_entry = {repository_name: str(repository_path.absolute())}

    global_config.repositories.update(repository_entry)
    global_config.default = repository_name
    global_config.dump()

    repo_config.migrate()

    click.echo('Successfully initialized the repository!')


def search(
    query: str, proxy: bool, extended: bool, attempt_download: bool, include_abstract: bool
) -> None:
    accumulator_thread = Thread(
        target=accumulate_search_results, args=(query, extended, attempt_download, include_abstract)
    )
    accumulator_thread.daemon = True
    accumulator_thread.start()

    repo_config.add_to_search_history(query)

    progress_bar.start()
    while not SEARCH_RESULTS:
        pass
    progress_bar.stop()

    if SEARCH_RESULTS == [NOTHING_FOUND_STR]:
        click.echo(NOTHING_FOUND_STR)
        return

    arxiv_streak = 0
    for index, result in enumerate(SEARCH_RESULTS):
        if not isinstance(result.value, SearchResult):
            continue

        if result.value.DOI.startswith('10.48550'):
            arxiv_streak += 1
        else:
            arxiv_streak = 0

        if arxiv_streak == DIVIDING_LINE_BOUNDARY:
            SEARCH_RESULTS.insert(index + 1, questionary.Separator())

    chosen_result = questionary.select(
        message='Choose the suitable paper to add to your library',
        choices=SEARCH_RESULTS,
        pointer='\u276f',
    ).ask()

    if chosen_result is not None:
        download(chosen_result, proxy)


def download(search_result: SearchResult, proxy: bool) -> None:
    headers = {'User-Agent': UA.random}
    proxy = global_config.proxy if proxy else None

    logger.info(f'Attempting to download a {search_result = !r} with {proxy = }')

    if not search_result.link_guarantee:
        click.echo('A downloadable version of this work could not be found automatically :(')

        if search_result.download_link:
            click.echo(
                f'However, you could try and download the paper '
                f"from the publisher's website manually: {search_result.download_link}"
            )

        repo_config.add_to_wishlist(search_result)
        return

    download_link = search_result.download_link
    if not download_link.startswith('http'):  # protocol missing
        download_link = 'http://' + download_link

    with httpx.Client(headers=headers, proxy=proxy, timeout=5, follow_redirects=True) as client:
        try:
            with client.stream('GET', download_link) as response:
                if response.status_code != HTTPStatus.OK:
                    repo_config.add_to_wishlist(search_result)

                    logger.warning(f'Download failed with {response.status_code = }')
                    return

                content_type = response.headers.get('Content-Type')
                if not any(
                    content_type.startswith(allowed_content_type)
                    for allowed_content_type in ('application/pdf', 'application/octet-stream')
                ):
                    repo_config.add_to_wishlist(search_result)

                    logger.warning(
                        f'Download failed as Content-Type of the page is "{content_type}"'
                    )
                    print(response.read())
                    return

                with open(repo_config.repo_path / search_result.filename, 'wb') as result_file:
                    for chunk in response.iter_bytes():
                        result_file.write(chunk)
        except httpx.TimeoutException:
            repo_config.add_to_wishlist(search_result)

            logger.warning(f'Download failed as {download_link} is not responding')
            return

    repo_config.add_to_content(search_result)

    click.echo('Successfully downloaded the paper!')


def open_pdf(query: str) -> str:
    query_dois = extract_dois(query)
    query_arxiv_ids = extract_arxiv_ids(query)
    query_ids = query_dois + query_arxiv_ids
    if len(query_ids) > 1:
        raise click.BadParameter('Specified too many IDs: impossible to open single paper')

    titles = [result['title'] for result in repo_config.content]
    dois = [result['DOI'] for result in repo_config.content]

    # noinspection PyTypeChecker
    # authors of the `rapidfuzz` library incorrectly specified the signature of the function
    best_title_match = process.extractOne(
        query, titles, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_RATE, processor=default_process
    )

    best_id_match = None
    if query_ids:
        # noinspection PyTypeChecker
        best_id_match = process.extractOne(
            query_ids[0],
            dois,
            scorer=fuzz.WRatio,
            score_cutoff=FUZZY_MATCH_RATE,
            processor=default_process,
        )

    if best_title_match is None and best_id_match is None:
        click.echo('Did not find any relevant papers :(')
        return ''

    best_match = best_id_match if best_id_match is not None else best_title_match
    logger.info(f'Best Match Relevance Score: {best_match[1]}')

    best_match_filename = SearchResult(**repo_config.content[best_match[2]]).filename
    best_match_path = str(repo_config.repo_path / best_match_filename)
    if ' ' in best_match_path:
        best_match_path = f'"{best_match_path}"'

    return best_match_path


@main.command('tutorial')
def tutorial_command():
    tutorial()


@main.command('init')
@click.argument('repository_path', nargs=-1, type=click.Path(file_okay=False, path_type=Path))
def init_command(repository_path: tuple[Path]):
    match len(repository_path):
        case 0:
            init()
        case 1:
            init(repository_path[0])
        case _:
            raise click.BadArgumentUsage('Exactly one path (or none at all) should be provided')


@main.command('open')
@click.argument('query', type=str)
def open_command(query: str):
    best_match_path = open_pdf(query)
    if best_match_path:
        _open_pdf(best_match_path)


@main.command('search')
@click.argument('query', type=str)
@click.option(
    '--proxy',
    is_flag=True,
    default=False,
    help='Whether to use a proxy in subsequent download requests',
)
@click.option(
    '--extended',
    is_flag=True,
    default=False,
    help='Whether to include abstract and other fields in the search. Defaults to False (search by title only)',
)
@click.option(
    '--attempt-download',
    is_flag=True,
    default=True,
    help='Whether to attempt download all papers on the server side. Defaults to True',
)
@click.option(
    '--include-abstract',
    is_flag=True,
    default=False,
    help='Whether to include abstracts to the received metadata (experimental feature). Defaults to False',
)
def search_command(
    query: str, proxy: bool, extended: bool, attempt_download: bool, include_abstract: bool
):
    search(query, proxy, extended, attempt_download, include_abstract)


if __name__ == '__main__':
    main()
