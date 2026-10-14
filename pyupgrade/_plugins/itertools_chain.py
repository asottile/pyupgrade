from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import tokens_to_src

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import arg_str
from pyupgrade._token_helpers import find_call
from pyupgrade._token_helpers import parse_call_args


def _fix_from_iterable(
        i: int,
        tokens: list[Token],
        *,
        parenthesize: bool,
) -> None:
    j = find_call(tokens, i)
    (arg,), end = parse_call_args(tokens, j)
    iterable = arg_str(tokens, *arg)
    if parenthesize:
        iterable = f'({tokens_to_src(tokens[slice(*arg)])})'
    src = f'(*it for it in {iterable})'
    tokens[i:end] = [Token('CODE', src)]


def _fix_chain_starred(
        i: int,
        tokens: list[Token],
        *,
        parenthesize: bool,
) -> None:
    j = find_call(tokens, i)
    (arg,), end = parse_call_args(tokens, j)

    # remove the first `*`
    for k in range(*arg):
        if tokens[k].matches(name='OP', src='*'):
            tokens[k] = tokens[k]._replace(src='')
            break
    else:
        raise AssertionError('did not find `*`?')

    iterable = arg_str(tokens, *arg)
    if parenthesize:
        iterable = f'({tokens_to_src(tokens[slice(*arg)])})'
    src = f'(*it for it in {iterable})'
    tokens[i:end] = [Token('CODE', src)]


def _fix_chain_to_iter(i: int, tokens: list[Token]) -> None:
    j = find_call(tokens, i)
    (arg,), end = parse_call_args(tokens, j)
    src = f'iter({arg_str(tokens, *arg)})'
    tokens[i:end] = [Token('CODE', src)]


def _fix_chain_multiple(i: int, tokens: list[Token]) -> None:
    j = find_call(tokens, i)
    args, end = parse_call_args(tokens, j)
    joined = ', '.join(arg_str(tokens, *arg) for arg in args)
    src = f'(*it for it in ({joined}))'
    tokens[i:end] = [Token('CODE', src)]


def _has_named_expr(node: ast.Call) -> bool:
    return any(
        isinstance(expr, ast.NamedExpr)
        for arg in node.args for expr in ast.walk(arg)
    )


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 15) and
            isinstance(node.func, ast.Attribute) and
            node.func.attr == 'from_iterable' and
            is_name_attr(
                node.func.value,
                state.from_imports,
                ('itertools',),
                ('chain',),
            ) and
            not has_starargs(node) and
            len(node.args) == 1 and
            not _has_named_expr(node)
    ):
        func = functools.partial(
            _fix_from_iterable,
            parenthesize=isinstance(
                node.args[0], (ast.GeneratorExp, ast.IfExp),
            ),
        )
        yield ast_to_offset(node), func
    elif (
            state.settings.min_version >= (3, 15) and
            is_name_attr(
                node.func,
                state.from_imports,
                ('itertools',),
                ('chain',),
            ) and
            not node.keywords and
            not _has_named_expr(node)
    ):
        if len(node.args) == 1 and isinstance(node.args[0], ast.Starred):
            func = functools.partial(
                _fix_chain_starred,
                parenthesize=isinstance(node.args[0].value, ast.IfExp),
            )
            yield ast_to_offset(node), func
        elif len(node.args) == 1:
            yield ast_to_offset(node), _fix_chain_to_iter
        else:
            yield ast_to_offset(node), _fix_chain_multiple
