import os
from pathlib import Path

import click

from utils import dump_json, load_json


@click.group()
def main():
    pass


@click.command()
@click.argument('repository_path', type=click.Path(file_okay=False, path_type=Path))
def init(repository_path: Path):
    os.makedirs(repository_path, exist_ok=True)

    scidock_root = Path('~/.scidock').expanduser()
    scidock_repo_root = repository_path / '.scidock'
    if Path(scidock_repo_root).exists():
        click.echo('Repository in this directory is already initialized!', err=True)
        return

    os.makedirs(scidock_repo_root)
    os.makedirs(scidock_root, exist_ok=True)

    # TODO: implement removing outdated repositories
    # TODO: come up with a solution with the problem of non-consecutive indices
    current_repositories = load_json(scidock_root / 'repositories.json')
    if current_repositories.get('repositories') is None:
        new_repository_id = '0'
        current_repositories['repositories'] = {}
    else:
        new_repository_id = str(max(map(int, current_repositories.get('repositories'))) + 1)

    new_repository_repr = {new_repository_id: {'path': str(scidock_repo_root.absolute())}}
    current_repositories['repositories'].update(new_repository_repr)
    current_repositories['default'] = new_repository_id

    dump_json({}, scidock_repo_root / 'content.json')
    dump_json(current_repositories, scidock_root / 'repositories.json')


if __name__ == '__main__':
    main.add_command(init)

    main()
