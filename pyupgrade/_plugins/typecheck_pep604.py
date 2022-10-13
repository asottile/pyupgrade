from __future__ import annotations

import ast
import functools
from typing import Iterable

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import State, TokenFunc, register
from pyupgrade._token_helpers import (
    find_open_paren,
    parse_call_args,
    replace_argument,
)
from tokenize_rt import Offset, Token


def _is_type_check(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"isinstance", "issubclass"}
    )


def _replace_to_union(i: int, tokens: list[Token], *, new: str) -> None:
    func_start = find_open_paren(tokens, i)
    func_args, _ = parse_call_args(tokens, func_start)
    replace_argument(
        1,  # we need to replace second argument
        tokens,
        func_args,
        new=new,
    )


@register(ast.Call)
def visit_Call(
    state: State,
    node: ast.Call,
    parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if state.settings.min_version >= (3, 10) and _is_type_check(node):
        type_args = node.args[1]
        if isinstance(type_args, ast.Tuple) and len(type_args.elts) > 1:
            new_value = []
            for expr in type_args.elts:
                if not isinstance(expr, ast.Name):
                    # do not support expressions other then type names
                    return
                new_value.append(expr.id)
            union_type = " | ".join(new_value)
            func = functools.partial(_replace_to_union, new=union_type)
            yield ast_to_offset(node), func
