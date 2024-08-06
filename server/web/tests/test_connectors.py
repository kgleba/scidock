# ruff: noqa: S101 - `assert` is at the heart of testing with `pytest`

from dataclasses import dataclass
from itertools import permutations

import pytest

from web.connectors import arxiv, crossref, nlp, scihub
from web.parsers.metadata import EmptySearchMeta

arxiv.MAX_RETRIES = 10


@dataclass
class NLPTestCase:
    query: str

    expected_keywords: dict[str, list[str]]
    expected_names: dict[str, list[str]]
    expected_clean_query: dict[str, str]


@dataclass
class arXivTestCase:  # noqa: N801
    query: str
    extended: bool

    expected_n_results: int
    expected_titles: list[str]


@dataclass
class CrossRefTestCase:
    query: str

    expected_n_results: int
    expected_titles: list[str]


@dataclass
class SciHubTestCase:
    doi: str

    expected_guarantee: bool


nlp_test_cases = [
    NLPTestCase(
        query='Assessment of Process Capability: the case of Soft Drinks Processing Unit by Kottala Sri Yogi',
        expected_keywords={
            'all-MiniLM-L6-v2': ['capability', 'drinks', 'kottala', 'process', 'soft']
        },
        expected_names={'en_core_web_sm': ['Sri Yogi'], 'en_core_web_trf': ['Kottala Sri Yogi']},
        expected_clean_query={
            'en_core_web_sm': 'assessment Process Capability case Soft Drinks Processing Unit Kottala Sri Yogi',
            'en_core_web_trf': 'Assessment process capability case Soft Drinks Processing Unit Kottala Sri Yogi',
        },
    )
]

arxiv_test_cases = [
    arXivTestCase(
        query='deep learning for symbolic calculations',
        extended=False,
        expected_n_results=arxiv.DATA_LIMIT,
        expected_titles=['Deep Learning for Symbolic Mathematics'],
    ),
    arXivTestCase(
        query='deep learning for symbolic computations',
        extended=True,
        expected_n_results=arxiv.DATA_LIMIT,
        expected_titles=[
            'Discovering Predictive Relational Object Symbols with Symbolic Attentive\n  Layers'
        ],
    ),
    arXivTestCase(
        query='2401.12070',
        extended=False,
        expected_n_results=1,
        expected_titles=[
            'Spotting LLMs With Binoculars: Zero-Shot Detection of Machine-Generated\n  Text'
        ],
    ),
]

crossref_test_cases = [
    CrossRefTestCase(
        query='meow 10.1088/1757-899X/330/1/012064',
        expected_n_results=101,
        expected_titles=[
            'Assessment of Process Capability: the case of Soft Drinks Processing Unit',
            'Mephedrone (4-methylcathinone; meow meow)',
            'MEOW',
            'Meow',
        ],
    ),
    CrossRefTestCase(
        query='Assessment of Process Capability: the case of Soft Drinks Processing Unit by Kottala Sri Yogi',
        expected_n_results=100,
        expected_titles=[
            'Assessment of Process Capability: the case of Soft Drinks Processing Unit'
        ],
    ),
]

scihub_test_cases = [
    SciHubTestCase('10.1371/journal.pmed.0040218.sd002', False),
    SciHubTestCase('10.1080/21598282.2017.1287585', True),
    SciHubTestCase('10.1163/2214-8647_bnps6_com_00229', False),
    SciHubTestCase('10.4236/ad.2022.104009', False),
    SciHubTestCase('10.1016/j.culher.2019.07.020', True),
    SciHubTestCase('10.5897/SRE12.383', True),
    SciHubTestCase('10.4236/ad.2015.34014', False),
    SciHubTestCase('10.1109/SENSOR.1995.721698', True),
    SciHubTestCase('10.1109/MEMSYS.1995.472541', True),
    SciHubTestCase('10.1007/978-1-4615-6297-9_7', False),
    SciHubTestCase('10.1016/0924-4247(96)01285-X', True),
]


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', nlp_test_cases)
async def test_nlp(test_case: NLPTestCase):
    nlp_edition = await nlp.get_edition()
    test_query = 'Assessment of Process Capability: the case of Soft Drinks Processing Unit by Kottala Sri Yogi'

    query_names = await nlp.extract_names(test_query)
    query_keywords = await nlp.extract_keywords(test_query)
    clean_query = await nlp.remove_stop_words(test_query)

    assert nlp_edition.get('keyword_model') in ('all-MiniLM-L6-v2',), 'Unknown keyword model'
    assert nlp_edition.get('nlp_model') in (
        'en_core_web_sm',
        'en_core_web_trf',
    ), 'Unknown NLP model'

    match nlp_edition['keyword_model']:
        case 'all-MiniLM-L6-v2':
            assert sorted(query_keywords) == test_case.expected_keywords['all-MiniLM-L6-v2']

    match nlp_edition['nlp_model']:
        case 'en_core_web_sm':
            assert query_names == test_case.expected_names['en_core_web_sm']
            assert clean_query == test_case.expected_clean_query['en_core_web_sm']
        case 'en_core_web_trf':
            assert query_names == test_case.expected_names['en_core_web_trf']
            assert clean_query == test_case.expected_clean_query['en_core_web_trf']


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', arxiv_test_cases)
async def test_arxiv(test_case: arXivTestCase):
    arxiv_results = await arxiv.search(test_case.query, extended=test_case.extended)

    assert len(arxiv_results) == test_case.expected_n_results

    assert all(result.title for result in arxiv_results)
    assert all(result.DOI for result in arxiv_results)
    assert all(result.authors for result in arxiv_results)
    assert all(result.abstract for result in arxiv_results)
    assert all(result.download_link for result in arxiv_results)
    assert all(
        result.relevance_score == EmptySearchMeta.relevance_score for result in arxiv_results
    )

    for result in arxiv_results:
        arxiv_id = result.DOI.removeprefix('10.48550/arXiv.')
        assert result.download_link.startswith(f'http://arxiv.org/pdf/{arxiv_id}')

    prefix_titles = [result.title for result in arxiv_results][: len(test_case.expected_titles)]
    assert prefix_titles == test_case.expected_titles


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', crossref_test_cases)
async def test_crossref(test_case: CrossRefTestCase):
    crossref_results = await crossref.search(test_case.query)

    assert len(crossref_results) == test_case.expected_n_results

    assert all(result.title for result in crossref_results)
    assert all(result.DOI for result in crossref_results)
    assert all(
        result.relevance_score != EmptySearchMeta.relevance_score for result in crossref_results
    )

    prefix_titles = tuple(result.title for result in crossref_results)[
        : len(test_case.expected_titles)
    ]
    assert prefix_titles in list(
        permutations(test_case.expected_titles)
    )  # CrossRef results are not deterministic :(


@pytest.mark.asyncio()
@pytest.mark.parametrize('test_case', scihub_test_cases)
async def test_scihub(test_case: SciHubTestCase):
    mirror = await scihub.establish_mirror()
    assert mirror in scihub.SCIHUB_MIRRORS + scihub.SCIDB_MIRRORS

    scihub_result = await scihub.get_download_link(test_case.doi)
    assert scihub_result.guarantee == test_case.expected_guarantee
