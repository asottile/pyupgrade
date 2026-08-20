from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_eq
from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import arg_str
from pyupgrade._token_helpers import Block
from pyupgrade._token_helpers import find_call
from pyupgrade._token_helpers import find_op
from pyupgrade._token_helpers import parse_call_args


def _fix(i: int, tokens: list[Token], *, name: str, func: str) -> None:
    block = Block.find(tokens, i, trim_end=True)
    j = find_op(tokens, i, '.')
    j = find_call(tokens, j)
    (arg,), _ = parse_call_args(tokens, j)

    newsrc = f'{name} = {name}.{func}({arg_str(tokens, *arg)})'

    start = block.start
    while tokens[start].name in {'INDENT', 'UNIMPORTANT_WS'}:
        start += 1

    end = block.end
    while tokens[end].name != 'NEWLINE':
        end -= 1

    tokens[start:end] = [Token('CODE', newsrc)]


@register(ast.If)
def visit_If(
        state: State,
        node: ast.If,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 9) and

            # cannot be `else` or `elif`
            not node.orelse and
            (
                not isinstance(parent, ast.If) or
                parent.col_offset != node.col_offset
            ) and

            # if whatever.<endswith|startswith>(...):
            isinstance(node.test, ast.Call) and
            isinstance(node.test.func, ast.Attribute) and
            isinstance(node.test.func.value, ast.Name) and
            not has_starargs(node.test) and
            len(node.test.args) == 1 and

            # whatever = ...
            len(node.body) == 1 and
            isinstance(node.body[0], ast.Assign) and
            len(node.body[0].targets) == 1 and
            isinstance(node.body[0].targets[0], ast.Name) and
            node.body[0].targets[0].id == node.test.func.value.id and

            # whatever[<someslice>]
            isinstance(node.body[0].value, ast.Subscript) and
            isinstance(node.body[0].value.value, ast.Name) and
            node.body[0].value.value.id == node.test.func.value.id and
            isinstance(node.body[0].value.slice, ast.Slice)
    ):
        slc = node.body[0].value.slice

        if (
                node.test.func.attr == 'startswith' and

                # [len(...):]
                slc.step is None and
                slc.upper is None and
                isinstance(slc.lower, ast.Call) and
                isinstance(slc.lower.func, ast.Name) and
                slc.lower.func.id == 'len' and
                not has_starargs(slc.lower) and
                len(slc.lower.args) == 1 and
                ast_eq(node.test.args[0], slc.lower.args[0])
        ):
            func = functools.partial(
                _fix,
                name=node.test.func.value.id,
                func='removeprefix',
            )
            yield ast_to_offset(node), func
        elif (
                node.test.func.attr == 'endswith' and

                slc.step is None and
                slc.lower is None and
                # -1
                isinstance(slc.upper, ast.BinOp) and
                isinstance(slc.upper.left, ast.UnaryOp) and
                isinstance(slc.upper.left.op, ast.USub) and
                isinstance(slc.upper.left.operand, ast.Constant) and
                slc.upper.left.operand.value == 1 and

                # *
                isinstance(slc.upper.op, ast.Mult) and

                # len(...)
                isinstance(slc.upper.right, ast.Call) and
                isinstance(slc.upper.right.func, ast.Name) and
                slc.upper.right.func.id == 'len' and
                not has_starargs(slc.upper.right) and
                len(slc.upper.right.args) == 1 and
                ast_eq(node.test.args[0], slc.upper.right.args[0])
        ):
            func = functools.partial(
                _fix,
                name=node.test.func.value.id,
                func='removesuffix',
            )
            yield ast_to_offset(node), func
