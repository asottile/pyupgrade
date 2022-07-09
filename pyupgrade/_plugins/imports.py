from __future__ import annotations

import ast
import functools
from typing import Iterable
from typing import Mapping
from typing import NamedTuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_end
from pyupgrade._token_helpers import find_token

# GENERATED VIA generate-imports
# Using reorder-python-imports==3.6.0
REMOVALS = {
    (2, 7): {'__future__': {'generators', 'nested_scopes', 'with_statement'}},
    (3,): {
        '__future__': {
            'absolute_import', 'division', 'print_function',
            'unicode_literals',
        },
        'builtins': {
            '*', 'ascii', 'bytes', 'chr', 'dict', 'filter', 'hex', 'input',
            'int', 'isinstance', 'list', 'map', 'max', 'min', 'next', 'object',
            'oct', 'open', 'pow', 'range', 'round', 'str', 'super', 'zip',
        },
        'io': {'open'},
        'six': {'callable', 'next'},
        'six.moves': {'filter', 'input', 'map', 'range', 'zip'},
    },
    (3, 7): {'__future__': {'generator_stop'}},
}
REMOVALS[(3,)]['six.moves.builtins'] = REMOVALS[(3,)]['builtins']
# END GENERATED


@functools.lru_cache(maxsize=None)
def _removals(version: tuple[int, ...]) -> Mapping[str, set[str]]:
    ret = {}
    for k, v in REMOVALS.items():
        if k <= version:
            ret.update(v)
    return ret


def _remove_import(i: int, tokens: list[Token]) -> None:
    del tokens[i:find_end(tokens, i)]


class FromImport(NamedTuple):
    mod_start: int
    mod_end: int
    names: tuple[int, ...]


def _parse_from_import(i: int, tokens: list[Token]) -> FromImport:
    j = i + 1
    # XXX: does not handle explicit relative imports
    while tokens[j].name != 'NAME':
        j += 1
    mod_start = j

    import_token = find_token(tokens, j, 'import')
    j = import_token - 1
    while tokens[j].name != 'NAME':
        j -= 1
    mod_end = j

    # XXX: does not handle `*` imports
    names = [
        j
        for j in range(import_token + 1, find_end(tokens, import_token))
        if tokens[j].name == 'NAME'
    ]
    for i in reversed(range(len(names))):
        if tokens[names[i]].src == 'as':
            del names[i:i + 2]

    return FromImport(mod_start, mod_end, tuple(names))


def _remove_import_partial(
        i: int,
        tokens: list[Token],
        *,
        idxs: list[int],
) -> None:
    parsed = _parse_from_import(i, tokens)

    for idx in reversed(idxs):
        if idx == 0:  # look forward until next name and del
            del tokens[parsed.names[idx]:parsed.names[idx + 1]]
        else:  # look backward for comma and del
            j = end = parsed.names[idx]
            while tokens[j].src != ',':
                j -= 1
            del tokens[j:end + 1]


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    removals = _removals(state.settings.min_version)
    if node.col_offset == 0 and node.level == 0 and node.module is not None:
        removals_for_mod = removals.get(node.module)
        if removals_for_mod is not None:
            idxs = [
                i
                for i, alias in enumerate(node.names)
                if not alias.asname and alias.name in removals_for_mod
            ]
            if len(idxs) == len(node.names):
                yield ast_to_offset(node), _remove_import
            elif idxs:
                func = functools.partial(_remove_import_partial, idxs=idxs)
                yield ast_to_offset(node), func
