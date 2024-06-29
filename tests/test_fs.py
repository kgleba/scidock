# ruff: noqa: S101, I001

import json
import shutil
from pathlib import Path

import pytest

from scidock import scidock
from . import SEARCH_TEST_CASES, SearchTestCase


@pytest.fixture(scope='session')
def test_path():
    path = Path('./test_repo')
    path.mkdir()

    yield path

    shutil.rmtree(path, ignore_errors=True)


def test_repo_init(test_path: Path):
    scidock.init(test_path, 'test_repo')

    assert (test_path / '.scidock').exists()
    assert (test_path / '.scidock' / 'content.json').exists()

    with open(test_path / '.scidock' / 'content.json', encoding='utf-8') as content_file:
        content = json.load(content_file)

    assert content == {'local': {}, 'recent_searches': {}}

    scidock_root = Path('~/.scidock').expanduser()

    assert scidock_root.exists()
    assert (scidock_root / 'config.json').exists()

    with open(scidock_root / 'config.json', encoding='utf-8') as config_file:
        config = json.load(config_file)

    assert config.get('repositories') == {'test_repo': {'path': str(test_path.absolute())}}
    assert config.get('default') == 'test_repo'
    assert config.get('proxy') == {}


def test_duplicate_init(test_path: Path):
    assert scidock.init(test_path, 'test_repo') is None


def test_init_default_change(tmp_path: Path):
    scidock.init(tmp_path, 'new_test_repo')

    scidock_root = Path('~/.scidock').expanduser()

    with open(scidock_root / 'config.json', encoding='utf-8') as config_file:
        config = json.load(config_file)

    assert config.get('default') == 'new_test_repo'


def test_init_path_only(tmp_path: Path):
    scidock.init(tmp_path)

    scidock_root = Path('~/.scidock').expanduser()

    with open(scidock_root / 'config.json', encoding='utf-8') as config_file:
        config = json.load(config_file)

    assert tmp_path.name in config.get('repositories', {})
    assert config.get('default') == tmp_path.name


@pytest.mark.parametrize('test_case', SEARCH_TEST_CASES)
def test_file_presence(test_path: Path, test_case: SearchTestCase):
    filenames = [file.name for file in test_path.glob('**/*')]

    if test_case.filename is not None:
        assert test_case.filename in filenames


def test_files_amount(test_path: Path):
    filenames = [file.name for file in test_path.glob('**/*') if file.is_file()]
    n_downloadable_testcases = len({test_case.filename for test_case in SEARCH_TEST_CASES if test_case.filename is not None})

    assert len(filenames) == n_downloadable_testcases
