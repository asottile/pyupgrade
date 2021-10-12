import ast
import functools
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_end
from pyupgrade._token_helpers import find_token

MOCK_MODULES = frozenset(('mock', 'mock.mock'))


def _add_import(i: int, tokens: List[Token], module: str, name: str, alias: Optional[str]) -> None:
    asname = ''
    if alias:
        asname = f' as {alias}'
    src = f'from {module} import {name}{asname}\n'
    tokens.insert(i, Token('CODE', src))


def _remove_import(i: int, tokens: List[Token]) -> None:
    j = i + 1
    while tokens[j].src not in {',', ')'} and tokens[j].name != 'NEWLINE':
        j += 1

    if tokens[j].src != ',':
        # Include previous comma when import is last in group
        while tokens[i].src != ',':
            i -= 1
    else:
        # Increment to include ',' in deletion
        j += 1
    del tokens[i:j]


def _fix_relative_import_mock(i: int, tokens: List[Token], name: ast.Name, n: int) -> None:
    j = find_token(tokens, i, 'mock')

    if n == 1:
        src = 'unittest'
        tokens[j:j + 1] = [tokens[j]._replace(name='NAME', src=src)]
    else:
        src = 'unittest.mock'
        tokens[j:j + 1] = [tokens[j]._replace(name='NAME', src=src)]
        idx = find_token(tokens, j + 1, 'mock')
        _remove_import(idx, tokens)
        _add_import(i, tokens, 'unittest', name.name, name.asname)


def _fix_import_from_mock(i: int, tokens: List[Token], names: List[ast.Name]) -> None:
    
    name = next((name for name in names if name.name == 'mock'), None)
    if name:
        _fix_relative_import_mock(i, tokens, name, len(names))
    else:
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
        func = functools.partial(_fix_import_from_mock, names=node.names)
        yield ast_to_offset(node), func


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
