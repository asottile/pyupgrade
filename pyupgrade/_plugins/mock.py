import ast
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_token

MOCK_MODULES = frozenset(('mock', 'mock.mock'))


def _fix_import_from_mock(i: int, tokens: List[Token]) -> None:
    j = find_token(tokens, i, 'mock')
    if (
            j + 2 < len(tokens) and
            tokens[j + 1].src == '.' and
            tokens[j + 2].src == 'mock'
    ):
        k = j + 2
    else:
        k = j
    src = 'unittest.mock'
    tokens[j:k + 1] = [tokens[j]._replace(name='NAME', src=src)]


def _fix_import_mock(i: int, tokens: List[Token]) -> None:
    j = find_token(tokens, i, 'mock')
    if (
            j + 2 < len(tokens) and
            tokens[j + 1].src == '.' and
            tokens[j + 2].src == 'mock'
    ):
        j += 2
    src = 'from unittest import mock'
    tokens[i:j + 1] = [tokens[j]._replace(name='NAME', src=src)]


def _fix_mock_mock(i: int, tokens: List[Token]) -> None:
    j = find_token(tokens, i + 1, 'mock')
    del tokens[i + 1:j + 1]


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            not state.settings.keep_mock and
            not node.level and
            node.module in MOCK_MODULES
    ):
        yield ast_to_offset(node), _fix_import_from_mock


@register(ast.Import)
def visit_Import(
        state: State,
        node: ast.Import,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            not state.settings.keep_mock and
            len(node.names) == 1 and
            node.names[0].name in MOCK_MODULES
    ):
        yield ast_to_offset(node), _fix_import_mock


@register(ast.Attribute)
def visit_Attribute(
        state: State,
        node: ast.Attribute,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            not state.settings.keep_mock and
            isinstance(node.value, ast.Name) and
            node.value.id == 'mock' and
            node.attr == 'mock'
    ):
        yield ast_to_offset(node), _fix_mock_mock
