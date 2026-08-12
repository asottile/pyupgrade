from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import find_named_arg
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._string_helpers import is_codec
from pyupgrade._token_helpers import delete_argument
from pyupgrade._token_helpers import find_op
from pyupgrade._token_helpers import parse_call_args


def _remove_encoding(i: int, tokens: list[Token], *, arg_idx: int) -> None:
    j = find_op(tokens, i, '(')
    func_args, _ = parse_call_args(tokens, j)
    delete_argument(arg_idx, tokens, func_args)


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 15) and
            isinstance(node.func, ast.Name) and
            node.func.id == 'open' and
            node.keywords
    ):
        encoding = find_named_arg(node, 'encoding')
        if (
                encoding is not None and
                isinstance(encoding.value, ast.Constant) and
                isinstance(encoding.value.value, str) and
                is_codec(encoding.value.value, 'utf-8')
        ):
            func = functools.partial(
                _remove_encoding,
                arg_idx=len(node.args) + encoding.arg_idx,
            )
            yield ast_to_offset(node), func
