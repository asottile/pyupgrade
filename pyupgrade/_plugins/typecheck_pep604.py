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
from pyupgrade._plugins.six_simple import is_type_check
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import replace_argument


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
    if state.settings.min_version >= (3, 10) and is_type_check(node):
        type_args = node.args[1]
        if isinstance(type_args, ast.Tuple) and len(type_args.elts) > 1:
            new_value = []
            for expr in type_args.elts:
                if not isinstance(expr, ast.Name):
                    # do not support expressions other then type names
                    return
                new_value.append(expr.id)
            union_type = ' | '.join(new_value)
            func = functools.partial(_replace_to_union, new=union_type)
            yield ast_to_offset(node), func
