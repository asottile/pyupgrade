from __future__ import annotations

import ast
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_token

COLLECTIONS_MODULE = 'collections'
ABC_CLASSES = {
    'Hashable',
    'Awaitable',
    'Coroutine',
    'AsyncIterable',
    'AsyncIterator',
    'Iterable',
    'Iterator',
    'Reversible',
    'Sized',
    'Container',
    'Collection',
    'MutableSet',
    'Mapping',
    'MutableMapping',
    'Sequence',
    'MutableSequence',
    'ByteString',
    'MappingView',
    'KeysView',
    'ItemsView',
    'ValuesView',
    'Generator',
    'AsyncGenerator',
}


def _fix_import_from_collections(i: int, tokens: list[Token]) -> None:
    j = find_token(tokens, i, 'collections')
    src = 'collections.abc'
    tokens[j] = tokens[j]._replace(name='NAME', src=src)


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            not state.settings.keep_mock and
            not node.level and
            node.module == COLLECTIONS_MODULE and
            all(alias.name in ABC_CLASSES for alias in node.names)
    ):
        yield ast_to_offset(node), _fix_import_from_collections
