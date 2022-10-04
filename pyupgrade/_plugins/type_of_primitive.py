from __future__ import annotations

import ast
import functools
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_open_paren

NUM_TYPES = {
    int: 'int',
    float: 'float',
    complex: 'complex',
}


def _rewrite_type_of_primitive(
        i: int,
        tokens: list[Token],
        *,
        src: str,
) -> None:
    open_paren = find_open_paren(tokens, i + 1)
    j = find_closing_bracket(tokens, open_paren)
    tokens[i] = tokens[i]._replace(src=src)
    del tokens[i + 1:j + 1]


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            isinstance(node.func, ast.Name) and
            node.func.id == 'type' and
            len(node.args) == 1
    ):
        if isinstance(node.args[0], ast.Str):
            func = functools.partial(
                _rewrite_type_of_primitive,
                src='str',
            )
            yield ast_to_offset(node), func
        elif isinstance(node.args[0], ast.Bytes):
            func = functools.partial(
                _rewrite_type_of_primitive,
                src='bytes',
            )
            yield ast_to_offset(node), func
        elif isinstance(node.args[0], ast.Num):
            func = functools.partial(
                _rewrite_type_of_primitive,
                src=NUM_TYPES[type(node.args[0].n)],
            )
            yield ast_to_offset(node), func
