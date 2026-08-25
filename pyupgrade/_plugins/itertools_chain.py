from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import arg_str
from pyupgrade._token_helpers import find_call
from pyupgrade._token_helpers import parse_call_args


def _fix_from_iterable(i: int, tokens: list[Token]) -> None:
    j = find_call(tokens, i)
    (arg,), end = parse_call_args(tokens, j)
    src = f'(*it for it in {arg_str(tokens, *arg)})'
    tokens[i:end] = [Token('CODE', src)]


def _fix_chain_starred(i: int, tokens: list[Token]) -> None:
    j = find_call(tokens, i)
    (arg,), end = parse_call_args(tokens, j)

    # remove the first `*`
    for k in range(*arg):
        if tokens[k].matches(name='OP', src='*'):
            tokens[k] = tokens[k]._replace(src='')
            break
    else:
        raise AssertionError('did not find `*`?')

    src = f'(*it for it in {arg_str(tokens, *arg)})'
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
            len(node.args) == 1
    ):
        yield ast_to_offset(node), _fix_from_iterable
    elif (
            state.settings.min_version >= (3, 15) and
            is_name_attr(
                node.func,
                state.from_imports,
                ('itertools',),
                ('chain',),
            ) and
            not node.keywords
    ):
        if len(node.args) == 1 and isinstance(node.args[0], ast.Starred):
            yield ast_to_offset(node), _fix_chain_starred
        elif len(node.args) == 1:
            yield ast_to_offset(node), _fix_chain_to_iter
        else:
            yield ast_to_offset(node), _fix_chain_multiple
