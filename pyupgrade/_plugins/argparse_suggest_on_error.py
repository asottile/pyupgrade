from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import find_named_arg
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import remove_arg_at_idx


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 15) and
            is_name_attr(
                node.func,
                state.from_imports,
                ('argparse',),
                'ArgumentParser',
            ) and
            node.keywords
    ):
        suggest_on_error = find_named_arg(node, 'suggest_on_error')
        if (
                suggest_on_error is not None and
                isinstance(suggest_on_error.value, ast.Constant) and
                suggest_on_error.value.value is True
        ):
            func = functools.partial(
                remove_arg_at_idx,
                arg_idx=len(node.args) + suggest_on_error.arg_idx,
            )
            yield ast_to_offset(node), func
