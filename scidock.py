from pathlib import Path

import click
import questionary

from search_engines import crossref
from ui import progress_bar
from utils import dump_json, load_json, remove_outdated_repos


@click.group()
def main():
    pass


@click.command()
@click.argument('repository_path', type=click.Path(file_okay=False, path_type=Path))
@click.option('--name', type=str, help='Name of the repository. Defaults to the name of the folder')
def init(repository_path: Path, name: str | None):
    scidock_root = Path('~/.scidock').expanduser()
    scidock_repo_root = repository_path / '.scidock'
    if Path(scidock_repo_root).exists():
        click.echo('Repository in this directory is already initialized!', err=True)
        return

    scidock_repo_root.mkdir(parents=True)
    scidock_root.mkdir(exist_ok=True)

    current_repositories = load_json(scidock_root / 'repositories.json')

    if current_repositories.get('repositories') is None:
        current_repositories['repositories'] = {}

    current_repositories['repositories'] = remove_outdated_repos(current_repositories['repositories'])

    if name is not None:
        new_repository_name = name
    else:
        parts_included = 1
        new_repository_name = repository_path.absolute().parts[-1]
        while new_repository_name in current_repositories['repositories']:
            parts_included += 1
            new_repository_name = '/'.join(repository_path.parts[-parts_included:])

    new_repository_repr = {new_repository_name: {'path': str(repository_path.absolute())}}
    current_repositories['repositories'].update(new_repository_repr)
    current_repositories['default'] = new_repository_name

    dump_json({}, scidock_repo_root / 'content.json')
    dump_json(current_repositories, scidock_root / 'repositories.json')

    click.echo('Successfully initialized repository!')


@click.command()
@click.argument('query', type=str)
def search(query: str):
    # TODO: Suggested Workflow
    # Users get suggestions based on the relevance score provided by CrossRef
    # They are also provided with the option to open a pager (like GNU less) and scroll through more data generated on the fly
    # If nothing is to their liking, we can proceed searching for preprints in arXiv or in Google Scholar
    # The final goal of the search process is to retrieve the DOI, then one can proceed to the download stage

    progress_bar.start()

    # approach of defining the cutoff value
    search_prefix = []
    prefix_score_ratios = []
    prefix_max = -1
    previous_score = 0

    # too slow for now, because `crossrefapi` has made the decision for the user
    # n_search_results = crossref.search_results_length(query)
    # if n_search_results > 10_000:  # arbitrary number, should be tweaked afterwards
    #     # TODO: Inquirer Confirm
    #     click.echo(f'There are more than {n_search_results:,} search results. Do you want to make your query more specific?')

    progress_bar.update('Searching the CrossRef database...')

    desired_paper = None
    search_results = iter(crossref.search(query))
    for search_result in search_results:
        search_prefix.append(str(search_result))

        prefix_max = max(prefix_max, search_result.relevance_score)
        prefix_score_ratios.append((search_result.relevance_score - previous_score) / prefix_max)
        if len(search_prefix) >= 8:  # noqa: PLR2004 - arbitrary number, should be tweaked afterwards
            progress_bar.stop()

            best_score_ratio = prefix_score_ratios.index(max(prefix_score_ratios[1:]))
            search_prefix.insert(best_score_ratio + 2, questionary.Separator())

            # noinspection PyTypeChecker
            # signature changes at a runtime
            desired_paper = questionary.select(message='Choose the suitable paper to add it to your library',
                                               choices=(search_prefix, search_results),
                                               pointer='\u276f').ask()
            break

    print(desired_paper)


main.add_command(init)
main.add_command(search)

if __name__ == '__main__':
    main()
