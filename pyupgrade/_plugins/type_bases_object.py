from __future__ import annotations

import ast
import functools
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import UNIMPORTANT_WS

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import delete_argument


def remove_base_class_from_type_call(
    i: int, tokens: list[Token], *, count: int
) -> None:
    token_list = [x.src for x in tokens]
    print(token_list)
    if count == 1:
        if "object" in token_list:
            idx = token_list.index("object")
            add = 2 if token_list[idx + 1] == "," else 1
            del tokens[idx: idx + add]
    elif count == 2:
            idx = token_list.index("object")
            add = 2 if token_list[idx + 1] == "," else 1
            del tokens[idx]


@register(ast.Call)
def visit_Call(
    state: State,
    node: ast.Call,
    parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
        isinstance(node.func, ast.Name)
        and node.func.id == "type"
        and len(node.args) > 1
        and isinstance(node.args[1], ast.Tuple)
        and any(
            isinstance(elt, ast.Name) and elt.id == "object"
            for elt in node.args[1].elts
        )
    ):
        for base in node.args[1].elts:
            if isinstance(base, ast.Name) and base.id == "object":
                func = functools.partial(
                    remove_base_class_from_type_call, count=len(node.args[1].elts)
                )
                yield ast_to_offset(base), func
