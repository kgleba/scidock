import os
from pathlib import Path

import click

from utils import dump_json, load_json, remove_outdated_repos


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
    current_repositories = remove_outdated_repos(current_repositories)

    if current_repositories.get('repositories') is None:
        current_repositories['repositories'] = {}

    if name is not None:
        new_repository_name = name
    else:
        parts_included = 1
        new_repository_name = repository_path.parts[-1]
        while new_repository_name in current_repositories.get('repositories'):
            parts_included += 1
            new_repository_name = '/'.join(repository_path.parts[-parts_included:])

    new_repository_repr = {new_repository_name: {'path': str(scidock_repo_root.absolute())}}
    current_repositories['repositories'].update(new_repository_repr)
    current_repositories['default'] = new_repository_name

    dump_json({}, scidock_repo_root / 'content.json')
    dump_json(current_repositories, scidock_root / 'repositories.json')

    click.echo('Successfully initialized repository!')


main.add_command(init)

if __name__ == '__main__':
    main()
