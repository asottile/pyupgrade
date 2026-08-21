from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_op
from pyupgrade._token_helpers import is_close
from pyupgrade._token_helpers import is_open

_DUNDER_TO_BUILTIN = {
    '__aiter__': 'aiter',
    '__anext__': 'anext',
}


def _find_op_backward(tokens: list[Token], i: int, src: str) -> int:
    while not tokens[i].matches(name='OP', src=src):
        i -= 1
    return i


def _find_name_no_nested(tokens: list[Token], i: int, dunder: str) -> int:
    depth = 0
    while depth or not tokens[i].matches(name='NAME', src=dunder):
        if is_open(tokens[i]):
            depth += 1
        elif is_close(tokens[i]):
            depth -= 1
        i += 1
    return i


def _fix(i: int, tokens: list[Token], *, dunder: str) -> None:
    # Remove dunder.
    dunder_i = _find_name_no_nested(tokens, i, dunder)
    attr = _find_op_backward(tokens, dunder_i, '.')
    call = find_op(tokens, dunder_i, '(')
    call_end = find_op(tokens, call, ')')
    del tokens[attr:call_end + 1]

    # Use builtin.
    tokens.insert(attr, Token('CODE', ')'))
    call_name = _DUNDER_TO_BUILTIN[dunder]
    tokens.insert(i, Token('CODE', f"{call_name}("))


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 10) and
            not node.args and
            not node.keywords and
            isinstance(node.func, ast.Attribute) and
            node.func.attr in _DUNDER_TO_BUILTIN
    ):
        func = functools.partial(_fix, dunder=node.func.attr)
        yield ast_to_offset(node), func
