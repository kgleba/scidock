import os
from dataclasses import dataclass
from pathlib import Path

import click

from search_engines import crossref
from utils import dump_json, load_json, remove_outdated_repos


@dataclass
class CrossRefItem:
    title: str
    DOI: str
    relevance_score: float


@click.group()
def main():
    pass


@click.command()
@click.argument('repository_path', type=click.Path(file_okay=False, path_type=Path))
@click.option('--name', type=str, help='Name of the repository. Defaults to the name of the folder')
def init(repository_path: Path, name: str | None):
    os.makedirs(repository_path, exist_ok=True)

    scidock_root = Path('~/.scidock').expanduser()
    scidock_repo_root = repository_path / '.scidock'
    if Path(scidock_repo_root).exists():
        click.echo('Repository in this directory is already initialized!', err=True)
        return

    os.makedirs(scidock_repo_root)
    os.makedirs(scidock_root, exist_ok=True)

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

    # approach of defining the cutoff value
    search_prefix = []
    prefix_score_ratios = []
    prefix_max = -1
    previous_score = 0

    n_search_results = crossref.search_results_length(query)
    if n_search_results > 10_000:
        # TODO: Inquirer Confirm
        click.echo(f'There are more than {n_search_results} search results. Do you want to make your query more specific?')

    for paper in crossref.search(query):
        search_result = CrossRefItem(' / '.join(paper['title']), paper['DOI'], paper['score'])
        search_prefix.append(search_result)

        prefix_max = max(prefix_max, search_result.relevance_score)
        prefix_score_ratios.append((search_result.relevance_score - previous_score) / prefix_max)
        if len(search_prefix) >= 10:  # arbitrary number, should be tweaked afterwards
            best_score_ratio = prefix_score_ratios.index(max(prefix_score_ratios[1:]))
            print(*search_prefix[:best_score_ratio + 1], sep='\n')
            break


main.add_command(init)
main.add_command(search)

if __name__ == '__main__':
    main()
