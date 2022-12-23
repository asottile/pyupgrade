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
    _: int, tokens: list[Token], *, arguments: list[ast.Name]
) -> None:
    inner_tokens = [x.id for x in arguments]
    type_start = find_open_paren(tokens, 0)
    bases_start = find_open_paren(tokens, type_start + 1)
    _, end = parse_call_args(tokens, bases_start)
    inner_tokens = remove_all(inner_tokens, "object")
    del tokens[bases_start + 1 :end - 1]
    count = 1
    for i, token in enumerate(inner_tokens):
        tokens.insert(bases_start + count, Token("NAME", token))
        count += 1
        if i != len(inner_tokens) - 1:
            tokens.insert(bases_start + count, Token("UNIMPORTANT_WS", " "))
            tokens.insert(bases_start + count, Token("OP", ","))
            count += 2
        elif len(inner_tokens) == 1:
            tokens.insert(bases_start + count, Token("OP", ","))


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
                    arguments=node.args[1].elts,
                )
                yield ast_to_offset(base), func
