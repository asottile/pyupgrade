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


def remove_all(the_list: list[str], item: str) -> list[str]:
    return [x for x in the_list if x != item]


def remove_base_class_from_type_call(
    i: int, tokens: list[Token], *, node_objs_count: int
) -> None:
    token_list = [x.src for x in tokens]
    print(tokens)
    type_start = find_open_paren(tokens, 0)
    bases_start = find_open_paren(tokens, type_start + 1)
    bases, end = parse_call_args(tokens, bases_start)
    inner_tokens = token_list[bases_start + 1 : end - 1]
    for token in [",", " ", "object"]:
        inner_tokens = remove_all(inner_tokens, token)
    print(inner_tokens)
    if len(inner_tokens) == 0:
        del tokens[bases_start + 1 :end - 1]
    if len(inner_tokens) == 1:
        del tokens[bases_start + 1 :end - 1]
        tokens.insert(bases_start + 1, Token("NAME", inner_tokens[0]))
        tokens.insert(bases_start + 2, Token("OP", ","))


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
                # TODO: send idx of the found object
                func = functools.partial(
                    remove_base_class_from_type_call,
                    node_objs_count=len(node.args[1].elts),
                )
                yield ast_to_offset(base), func
