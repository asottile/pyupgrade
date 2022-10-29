from __future__ import annotations

import ast
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_token
from pyupgrade._token_helpers import remove_brace


def _replace_unpack_with_star(i: int, tokens: list[Token]) -> None:
    start = find_token(tokens, i, '[')
    end = find_closing_bracket(tokens, start)

    remove_brace(tokens, end)
    # replace `Unpack` with `*`
    tokens[i:start + 1] = [tokens[i]._replace(name='OP', src='*')]


@register(ast.Subscript)
def visit_Subscript(
    state: State,
    node: ast.Subscript,
    parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if state.settings.min_version < (3, 11):
        return

    if is_name_attr(node.value, state.from_imports, ('typing',), ('Unpack',)):
        if isinstance(parent, (ast.Subscript, ast.Index)):
            yield ast_to_offset(node.value), _replace_unpack_with_star
