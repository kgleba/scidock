# ruff: noqa: RUF001

from dataclasses import dataclass


@dataclass
class SearchTestCase:
    query: str
    position: int
    title: str
    filename: str | None


SEARCH_TEST_CASES = [
    SearchTestCase('deep learning for symbolic mathematics', 4,
                   'Deep Learning for Symbolic Mathematics. DOI: 10.48550/arXiv.1912.01412v1',
                   '1912.01412v1.Deep_Learning_for_Symbolic_Mathematics.pdf'),

    SearchTestCase('deep learning for symbolic mathematics by guillaume lample', 8,
                   'Deep Learning for Symbolic Mathematics. DOI: 10.48550/arXiv.1912.01412v1',
                   '1912.01412v1.Deep_Learning_for_Symbolic_Mathematics.pdf'),

    SearchTestCase('soft drinks processing unit assessment', 1,
                   'Assessment of Process Capability: The Case of Soft Drinks Processing Unit. DOI: 10.2139/ssrn.3060367', None),

    SearchTestCase('soft drinks processing unit assessment', 2,
                   'Assessment of Process Capability: the case of Soft Drinks Processing Unit. DOI: 10.1088/1757-899x/330/1/012064',
                   '10.1088.1757-899x.330.1.012064.Assessment_of_Process_Capability_the_case_of_Soft_Drinks_Processing_Unit_IOP_Conference_Series_Materials_Science_and_Engineering_330_012064.pdf'),

    SearchTestCase("who's downloading pirated papers", 1,
                   "Who's downloading pirated papers? Everyone. DOI: 10.1126/science.aaf5664", None),

    SearchTestCase("who's downloading pirated papers", 2,
                   "Who's downloading pirated papers? Everyone. DOI: 10.1126/science.352.6285.508",
                   '10.1126.science.352.6285.508.Who’s_downloading_pirated_papers_Everyone_Science_3526285_508–512.pdf'),

    SearchTestCase('10.1016/j.ipm.2005.12.001', 1,
                   'Automatic extraction of titles from general documents using machine learning. DOI: 10.1016/j.ipm.2005.12.001',
                   '10.1016.j.ipm.2005.12.001.Automatic_extraction_of_titles_from_general_documents_using_machine_learning_Information_Processing__Management_425_1276–1293.pdf'),

    SearchTestCase('10.1016/j.ipm.2005.12.001', 666,
                   'Automatic extraction of titles from general documents using machine learning. DOI: 10.1016/j.ipm.2005.12.001',
                   '10.1016.j.ipm.2005.12.001.Automatic_extraction_of_titles_from_general_documents_using_machine_learning_Information_Processing__Management_425_1276–1293.pdf'),

    SearchTestCase('1609.05521v2', 1,
                   'Playing FPS Games with Deep Reinforcement Learning. DOI: 10.48550/arXiv.1609.05521v2',
                   '1609.05521v2.Playing_FPS_Games_with_Deep_Reinforcement_Learning.pdf'),

    SearchTestCase('math', 64,
                   'Cyclic b-Multiplicative (A|,|B)-Hardy–Rogers-Type Local Contraction '
                   'and Related Results in b-Multiplicative and b-Metric Spaces. DOI: 10.1155/2020/2460702',
                   '10.1155.2020.2460702.Cyclic__b_Multiplicative____A__B___Hardy–RogersType_Local_Contraction_and_Related_Results_in__b_Multiplicative'
                   '_and__b_Metric_Spaces_Journal_of_Mathematics_2020_1–9.pdf')
]
