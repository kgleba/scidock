# ruff: noqa: S101, I001

import re
from pathlib import Path

import pexpect
import pytest

from scidock import main as scidock
from . import SEARCH_TEST_CASES, SearchTestCase

# source: https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


@pytest.fixture(scope='session')
def _init_repo():
    scidock.init(Path('./repo'))

    scidock.global_config.server_url = (
        'http://127.0.0.1:8080'  # assuming that server for the tests is launched locally
    )
    scidock.global_config.dump()


@pytest.mark.usefixtures('_init_repo')
@pytest.mark.flaky(max_runs=3)
@pytest.mark.parametrize('test_case', SEARCH_TEST_CASES)
def test_search_tui(test_case: SearchTestCase):
    query = test_case.query
    step = test_case.position - 1
    expected_title = test_case.title

    process = pexpect.spawn(f'scidock search "{query}"')
    process.expect('Choose the suitable paper to add to your library')
    process.send(b'\x1b[B' * step + b'\x0d')
    process.expect(pexpect.EOF)

    response = process.before.decode()
    response = re.sub(ANSI_ESCAPE_PATTERN, '', response)
    response = response.replace('\r', '').replace('\n', '')

    assert 'Download failed' not in response
    assert any(
        verdict in response
        for verdict in (
            'Successfully downloaded the paper!',
            'A downloadable version of this work could not be found automatically :(',
        )
    )

    assert f'Choose the suitable paper to add to your library {expected_title}' in response


def test_nonsensical_inputs():
    query = 'abacabadabacaba'

    process = pexpect.spawn(f'scidock search "{query}"')
    process.expect(pexpect.EOF)

    response = process.before.decode()

    assert 'Nothing found! :(' in response
