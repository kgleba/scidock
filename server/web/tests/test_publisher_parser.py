# ruff: noqa: S101 - `assert` is at the heart of testing with `pytest`

import time
from dataclasses import dataclass

import aiohttp
import pytest
import pytest_asyncio

from web.parsers import publishers
from web.parsers.metadata import EmptyLinkMeta, LinkMeta

MAX_AVG_EXECUTION_TIME = 0.05
MAX_EXECUTION_TIME = 5


@dataclass
class PublisherTestCase:
    doi: str

    expected_link: LinkMeta


reject_test_cases = [
    '10.1016/j.epsr.2024.110112',
    '10.1007/978-1-4842-6321-1_5',
    '10.1201/9781003226277-5',
    '10.4324/9781315282138',
]

publishers_test_cases = [
    PublisherTestCase(
        '10.48029/nji.1974.lxv1104',
        LinkMeta('https://www.tnaijournal-nji.com/admin/assets/article/pdf/11399_pdf.pdf', True),
    ),
    PublisherTestCase(
        '10.48550/arXiv.1912.01412', LinkMeta('https://arxiv.org/pdf/1912.01412', True)
    ),
    PublisherTestCase(
        '10.1109/ACCESS.2022.3143524',
        LinkMeta('https://ieeexplore.ieee.org/ielx7/6287639/9668973/09682708.pdf', True),
    ),
    PublisherTestCase(
        '10.5772/intechopen.111651',
        LinkMeta('https://www.intechopen.com/chapter/pdf-download/87170', True),
    ),
    PublisherTestCase(
        '10.3390/electronics13071407',
        LinkMeta('https://www.mdpi.com/2079-9292/13/7/1407/pdf', True),
    ),
    PublisherTestCase(
        '10.21203/rs.3.rs-2070234/v1',
        LinkMeta('https://www.researchsquare.com/article/rs-2070234/v1', False),
    ),
    PublisherTestCase(
        '10.2991/icmemm-18.2019.22',
        LinkMeta('https://www.atlantis-press.com/proceedings/icmemm-18/55914185', False),
    ),
    PublisherTestCase(
        '10.5176/2315-4330_wnc15.68',
        LinkMeta(
            'https://www.dropbox.com/scl/fi/u5ksv43820z6bhx45wz2k/WNC_2015_Proceedings_V1_Paper_30.pdf?rlkey=c7ialwzw1zfzzg5l69ecq04oi&dl=0',
            False,
        ),
    ),
    # PublisherTestCase(
    #     '10.1145/3639592.3639601', LinkMeta('https://dl.acm.org/doi/10.1145/3639592.3639601', False)
    # ), # investigate later
    PublisherTestCase('10.1037/e611302012-003', EmptyLinkMeta),
    PublisherTestCase('10.1061/(asce)st.1943-541x.0003405', EmptyLinkMeta),
    PublisherTestCase('10.1093/oso/9780195098709.001.0001', EmptyLinkMeta),
    PublisherTestCase('10.1063/5.0184450', EmptyLinkMeta),
]


# TODO: fix chapters issue for IntechOpen DOI: 10.5772/intechopen.1006093 and add to tests
# TODO: make "might be interesting" algorithm more robust and add DOIs:
#  '10.1145/3647782.3647815' as `EmptyLinkMeta`


@pytest_asyncio.fixture()
async def session():
    async with aiohttp.ClientSession() as sess:
        yield sess


def test_publisher_rejection_coverage():
    assert all(
        test_case.startswith(doi)
        for doi, test_case in zip(
            sorted(publishers.PUBLISHER_BLACKLIST), sorted(reject_test_cases), strict=True
        )
    )


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', reject_test_cases)
async def test_publisher_rejection(test_case: str, session: aiohttp.ClientSession):
    n_runs = 1_000
    execution_time = 0

    for _ in range(n_runs):
        start_time = time.perf_counter()
        await publishers.get_download_link(test_case, session)
        execution_time += time.perf_counter() - start_time

        if execution_time > MAX_EXECUTION_TIME:
            pytest.fail('Early return (due to presence in the blacklist) failed!')

    avg_execution_time = execution_time / n_runs
    assert avg_execution_time < MAX_AVG_EXECUTION_TIME


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', publishers_test_cases)
async def test_publisher(test_case: PublisherTestCase, session: aiohttp.ClientSession):
    download_link = await publishers.get_download_link(test_case.doi, session)
    assert download_link == test_case.expected_link
