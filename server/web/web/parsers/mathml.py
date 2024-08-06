import re
import xml.etree.ElementTree as ET  # noqa: N817 - naming convention for ElementTree
from collections.abc import Callable
from functools import partial
from itertools import zip_longest
from typing import Any

from defusedxml import ElementTree as DET  # noqa: N814 - naming convention for ElementTree

NODE_TAGS = ('mfenced', 'mfrac', 'msub', 'msubsup', 'msup', 'mroot')
LEAF_TAGS = ('mi', 'mn', 'mo', 'msqrt', 'ms')
IRRELEVANT_TAGS = (
    'maction',
    'menclose',
    'merror',
    'mglyph',
    'mlabeledtr',
    'mmultiscripts',
    'mover',
    'mpadded',
    'mphantom',
    'mrow',
    'style',
    'mspace',
    'mtable',
    'mtd',
    'mtext',
    'mtr',
    'mth',
    'munder',
    'munderover',
    'semantics',
)


def parse_document(document: str):
    document = re.sub(r'mml:(\w+)', '\1', document)

    for irrelevant_tag in IRRELEVANT_TAGS:
        document = re.sub(f'<{irrelevant_tag}[^>]*>', '', document)
        document = re.sub(f'</{irrelevant_tag}>', '', document)

    index_delta = 0
    for math_tag in re.finditer(r'<math[^>]*>(.+?)</math>', document, re.MULTILINE | re.DOTALL):
        new_value = parse_tag(math_tag.group(0))
        start, end = math_tag.span()

        document_chars = list(document)
        document_chars[start + index_delta : end + index_delta] = list(new_value)
        document = ''.join(document_chars)

        index_delta += len(new_value) - (end - start)

    return re.sub('</math>', '', document)


def extract_source(element: ET.Element) -> str:
    tag = re.sub('({[^}]*})?([^>]*)', r'\2', element.tag)
    text = (
        element.text if not list(element) else ''.join(extract_source(child) for child in element)
    )
    formatted_attrs = ' '.join(f'{key}="{value}"' for key, value in element.items())
    return f'<{tag} {formatted_attrs}>{text}</{tag}>'


def dynamic_join(
    separators: str, source: Callable[[int], Any], n_elements: int | None = None
) -> str:
    if n_elements is None:
        n_elements = len(separators) + 1

    if len(separators) != n_elements - 1:
        separators = separators[:-1] + separators[-1] * (n_elements - len(separators))

    elements = [str(source(i)) for i in range(n_elements)]

    joined_elements = ''
    for element, separator in zip_longest(elements, separators, fillvalue=''):
        joined_elements += element + separator

    return joined_elements


def parse_tag(tag: str) -> str:
    tag = tag.strip()

    root = DET.fromstring(tag)

    if root.tag.endswith('math'):
        return ''.join(parse_tag(extract_source(child)) for child in root)

    if root.tag in LEAF_TAGS:
        match root.tag:
            case 'mi' | 'mn' | 'mo':
                return root.text
            case 'ms':
                return f'"{root.text}"'
            case 'msqrt':
                return '√' + root.text

    join_sources = partial(dynamic_join, source=lambda i: parse_tag(extract_source(root[i])))
    tag_separators = {'mroot': '√', 'msub': '_', 'msup': '^', 'msubsup': '^_', 'mfrac': '/'}

    if root.tag in NODE_TAGS:
        match root.tag:
            case 'mfenced':
                open_, close, separators = (
                    root.attrib.get('open', '('),
                    root.attrib.get('close', ')'),
                    root.attrib.get('separators', ','),
                )
                return open_ + join_sources(separators, n_elements=len(list(root))) + close
            case _:
                return join_sources(tag_separators[root.tag])

    return ''
