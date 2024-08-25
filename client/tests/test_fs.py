# ruff: noqa: S101, I001

import json
import shutil
from pathlib import Path

import pytest

from scidock import main as scidock
from . import SEARCH_TEST_CASES, SearchTestCase


@pytest.fixture(scope='session')
def test_path():
    path = Path('./test_repo')
    path.mkdir()

    yield path

    shutil.rmtree(path, ignore_errors=True)


def test_repo_init(test_path: Path):
    scidock.init(test_path)

    content_path = test_path / '.scidock' / 'content.json'

    assert (test_path / '.scidock').exists()
    assert content_path.exists()

    with open(content_path, encoding='utf-8') as content_file:
        content = json.load(content_file)

    assert content == {
        'path': str(content_path.absolute()),
        'content': [],
        'wishlist': [],
        'search_history': [],
    }

    scidock_root = Path('~/.scidock').expanduser()

    assert scidock_root.exists()
    assert (scidock_root / 'config.json').exists()

    with open(scidock_root / 'config.json', encoding='utf-8') as config_file:
        config = json.load(config_file)

    assert config.get('repositories') == {'test_repo': str(test_path.absolute())}
    assert config.get('default') == 'test_repo'
    assert config.get('proxy') is None


def test_duplicate_init(test_path: Path):
    assert scidock.init(test_path) is None


def test_init_default_change(tmp_path: Path):
    scidock.init(tmp_path)

    scidock_root = Path('~/.scidock').expanduser()

    with open(scidock_root / 'config.json', encoding='utf-8') as config_file:
        config = json.load(config_file)

    assert tmp_path.name in config.get('repositories', {})
    assert config.get('default') == tmp_path.name


@pytest.mark.parametrize('test_case', SEARCH_TEST_CASES)
def test_file_presence(test_case: SearchTestCase):
    test_path = Path('./repo')
    filenames = [file.name for file in test_path.glob('*') if file.is_file()]

    if test_case.filename is not None:
        assert test_case.filename in filenames


def test_files_amount():
    test_path = Path('./repo')
    filenames = [file.name for file in test_path.glob('*') if file.is_file()]
    n_downloadable_testcases = len(
        {test_case.filename for test_case in SEARCH_TEST_CASES if test_case.filename is not None}
    )

    assert len(filenames) == n_downloadable_testcases
