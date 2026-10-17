from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import remove_base_class
from pyupgrade._token_helpers import UNIMPORTANT_WS


def _empty_tuple(i: int, tokens: list[Token]) -> None:
    left = i
    right = find_closing_bracket(tokens, i)
    while True:
        prev_i = left - 1
        while prev_i >= 0 and tokens[prev_i].name == UNIMPORTANT_WS:
            prev_i -= 1
        next_i = right + 1
        while next_i < len(tokens) and tokens[next_i].name == UNIMPORTANT_WS:
            next_i += 1
        if (
                prev_i >= 0 and
                next_i < len(tokens) and
                tokens[prev_i].src == '(' and
                tokens[next_i].src == ')'
        ):
            left = prev_i
            right = next_i
        else:
            break
    tokens[left] = tokens[left]._replace(src='()')
    del tokens[left + 1:right + 1]


@register(ast.ClassDef)
def visit_ClassDef(
        state: State,
        node: ast.ClassDef,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == 'object':
            yield ast_to_offset(base), remove_base_class


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            isinstance(node.func, ast.Name) and
            node.func.id == 'type' and
            len(node.args) == 3 and
            isinstance(node.args[1], ast.Tuple) and
            len(node.args[1].elts) == 1 and
            isinstance(node.args[1].elts[0], ast.Name) and
            node.args[1].elts[0].id == 'object'
    ):
        yield ast_to_offset(node.args[1]), _empty_tuple
