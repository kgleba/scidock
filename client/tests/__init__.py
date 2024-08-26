# ruff: noqa: RUF001

from dataclasses import dataclass

__all__ = ('SearchTestCase', 'SEARCH_TEST_CASES')

_certain_emoji = chr(9745) + '  '  # see meta/__init__.py
_uncertain_emoji = '🔎 '
_nothing_found_emoji = '❌ '


@dataclass
class SearchTestCase:
    query: str
    position: int
    title: str
    filename: str | None


SEARCH_TEST_CASES = [
    SearchTestCase(
        query='deep learning for symbolic mathematics',
        position=4,
        title=_certain_emoji
        + 'Deep Learning for Symbolic Mathematics. DOI: 10.48550/arXiv.1912.01412',
        filename='1912.01412.Deep_Learning_for_Symbolic_Mathematics.pdf',
    ),
    SearchTestCase(
        query='deep learning for symbolic mathematics by guillaume lample',
        position=4,
        title=_certain_emoji
        + 'Deep Learning for Symbolic Mathematics. DOI: 10.48550/arXiv.1912.01412',
        filename='1912.01412.Deep_Learning_for_Symbolic_Mathematics.pdf',
    ),
    SearchTestCase(
        query='soft drinks processing unit assessment',
        position=1,
        title=_certain_emoji
        + 'Assessment of Process Capability: the case of Soft Drinks Processing Unit. DOI: 10.1088/1757-899x/330/1/012064',
        filename='10.1088.1757-899x.330.1.012064.Assessment_of_Process_Capability_the_case_of_Soft_Drinks_Processing_Unit_IOP_Conference_Series_Materials_Science_and_Engineering_330_012064.pdf',
    ),
    SearchTestCase(
        query='soft drinks processing unit assessment',
        position=2,
        title=_nothing_found_emoji
        + 'Assessment of Process Capability: The Case of Soft Drinks Processing Unit. DOI: 10.2139/ssrn.3060367',
        filename=None,
    ),
    SearchTestCase(
        query="who's downloading pirated papers",
        position=1,
        title=_nothing_found_emoji
        + "Who's downloading pirated papers? Everyone. DOI: 10.1126/science.aaf5664",
        filename=None,
    ),
    SearchTestCase(
        query="who's downloading pirated papers",
        position=2,
        title=_certain_emoji
        + "Who's downloading pirated papers? Everyone. DOI: 10.1126/science.352.6285.508",
        filename='10.1126.science.352.6285.508.Who’s_downloading_pirated_papers_Everyone_Science_3526285_508–512.pdf',
    ),
    SearchTestCase(
        query='10.1016/j.ipm.2005.12.001',
        position=1,
        title=_certain_emoji
        + 'Automatic extraction of titles from general documents using machine learning. DOI: 10.1016/j.ipm.2005.12.001',
        filename='10.1016.j.ipm.2005.12.001.Automatic_extraction_of_titles_from_general_documents_using_machine_learning_Information_Processing_Management_425_1276–1293.pdf',
    ),
    SearchTestCase(
        query='10.1016/j.ipm.2005.12.001',
        position=666,
        title=_certain_emoji
        + 'Automatic extraction of titles from general documents using machine learning. DOI: 10.1016/j.ipm.2005.12.001',
        filename='10.1016.j.ipm.2005.12.001.Automatic_extraction_of_titles_from_general_documents_using_machine_learning_Information_Processing_Management_425_1276–1293.pdf',
    ),
    SearchTestCase(
        query='1609.05521v2',
        position=1,
        title=_certain_emoji
        + 'Playing FPS Games with Deep Reinforcement Learning. DOI: 10.48550/arXiv.1609.05521',
        filename='1609.05521.Playing_FPS_Games_with_Deep_Reinforcement_Learning.pdf',
    ),
    SearchTestCase(
        query='10.1155/2020/2460702',
        position=1,
        title=_certain_emoji
        + 'Cyclic b-Multiplicative (A|,|B)-Hardy–Rogers-Type Local Contraction '
        'and Related Results in b-Multiplicative and b-Metric Spaces. DOI: 10.1155/2020/2460702',
        filename=None,
    ),
]
