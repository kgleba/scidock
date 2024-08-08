# ruff: noqa: S101 - `assert` is at the heart of testing with `pytest`

import json
from dataclasses import asdict, dataclass
from functools import reduce
from operator import add
from typing import Any

import httpx
import pytest
import pytest_asyncio
from httpx_sse import aconnect_sse
from sse_starlette.sse import AppStatus

from web.main import app

AppStatus.should_exit_event = None


@dataclass
class SearchTestCase:
    query: str
    extended: bool
    attempt_download: bool
    include_abstract: bool


search_test_cases = [
    SearchTestCase(
        query='deep learning for symbolic calculations',
        extended=False,
        attempt_download=True,
        include_abstract=False,
    ),
    SearchTestCase(
        query='deep learning for symbolic calculations',
        extended=False,
        attempt_download=False,
        include_abstract=False,
    ),
    SearchTestCase(
        query='deep learning for symbolic calculations',
        extended=True,
        attempt_download=False,
        include_abstract=True,
    ),
    SearchTestCase(
        query='Assessment of Process Capability: the case of Soft Drinks Processing Unit by Kottala Sri Yogi',
        extended=False,
        attempt_download=True,
        include_abstract=False,
    ),
    SearchTestCase(
        query='Assessment of Process Capability: the case of Soft Drinks Processing Unit by Kottala Sri Yogi',
        extended=False,
        attempt_download=False,
        include_abstract=True,
    ),
]


def check_dict_type_conformity(
    dictionary: dict[str, Any],
    type_dict: dict[str, type[int | str | float]],
) -> bool:
    for key, value in dictionary.items():
        value_type = type_dict.get(key)
        if value_type is not None:  # noqa: SIM102
            if not isinstance(value, value_type):
                return False

    return True


@pytest.fixture(autouse=True)
def _reset_sse_starlette_app_status_event():
    # https://github.com/sysid/sse-starlette/issues/59
    from sse_starlette.sse import AppStatus

    AppStatus.should_exit_event = None


@pytest_asyncio.fixture()
async def session():
    # noinspection PyTypeChecker
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url='http://localhost') as client:
        yield client


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', search_test_cases)
async def test_search(test_case: SearchTestCase, session: httpx.AsyncClient):
    async with aconnect_sse(session, 'GET', '/search', params=asdict(test_case)) as event_source:
        data = reduce(add, [json.loads(sse.data) async for sse in event_source.aiter_sse()])

    response_model = {
        'title': str,
        'DOI': str,
        'authors': list,
        'download_link': str,
        'link_guarantee': bool,
    }

    if test_case.include_abstract:
        response_model.update({'abstract': str})

    assert all(sorted(response) == sorted(response_model) for response in data)
    assert all(check_dict_type_conformity(response, response_model) for response in data)

    # TODO: check how related is each of the responses to the query (e.g., using embeddings)
