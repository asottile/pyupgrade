from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_name
from pyupgrade._token_helpers import find_op
from pyupgrade._token_helpers import parse_call_args


def _convert_to_sentinel(i: int, tokens: list[Token]) -> None:
    start = find_name(tokens, i + 1, 'object')
    paren = find_op(tokens, start + 1, '(')
    _, end = parse_call_args(tokens, paren)
    tokens[start:end] = [Token('CODE', f'sentinel({tokens[i].src!r})')]


@register(ast.Assign)
def visit_Assign(
        state: State,
        node: ast.Assign,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 15) and
            len(node.targets) == 1 and
            isinstance(node.targets[0], ast.Name) and
            node.targets[0].col_offset == 0 and
            isinstance(node.value, ast.Call) and
            isinstance(node.value.func, ast.Name) and
            node.value.func.id == 'object' and
            not node.value.args and not node.value.keywords
    ):
        yield ast_to_offset(node), _convert_to_sentinel
