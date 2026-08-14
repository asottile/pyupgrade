from __future__ import annotations

import ast
from collections.abc import Iterable
from typing import NamedTuple

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import tokens_to_src
from tokenize_rt import UNIMPORTANT_WS

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import is_close
from pyupgrade._token_helpers import is_open


class _Comp(NamedTuple):
    for_idx: int
    in_idx: int


def _find_comps(i: int, tokens: list[Token]) -> tuple[list[_Comp], int]:
    assert is_open(tokens[i]), tokens[i]

    ret = []

    depth = 1
    async_idx = for_idx = None

    while depth:
        i += 1
        token = tokens[i]
        if is_open(token):
            depth += 1
        elif is_close(token):
            depth -= 1
        elif depth == 1:
            if token.matches(name='NAME', src='async'):
                async_idx = i
            elif token.matches(name='NAME', src='for'):
                for_idx = i
            elif for_idx is not None and token.matches(name='NAME', src='in'):
                ret.append(_Comp(async_idx or for_idx, i))
                async_idx = for_idx = None

    return ret, i


def _and_ws_before(i: int, tokens: list[Token]) -> int:
    while i > 0 and tokens[i - 1].name == UNIMPORTANT_WS:
        i -= 1
    return i


def _and_ws_after(i: int, tokens: list[Token]) -> int:
    while tokens[i + 1].name == UNIMPORTANT_WS:
        i += 1
    return i


def _fix_seq(i: int, tokens: list[Token]) -> None:
    comps, end = _find_comps(i, tokens)

    iter_start = _and_ws_after(comps[-1].in_idx, tokens) + 1
    splatted = tokens_to_src(tokens[iter_start:end])

    del_start = _and_ws_before(comps[-1].for_idx, tokens)
    end_of_elt = _and_ws_before(comps[0].for_idx, tokens)

    del tokens[del_start:end]
    tokens[i + 1:end_of_elt] = [Token('CODE', f'*{splatted}')]


def _visit_func(
        state: State,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            (
                state.settings.min_version >= (3, 15) or
                len(node.generators) == 1
            ) and
            isinstance(node.elt, ast.Name) and
            not node.generators[-1].ifs and
            not node.generators[-1].is_async and
            isinstance(node.generators[-1].target, ast.Name) and
            node.elt.id == node.generators[-1].target.id and (
                # foo(x for x in y) => foo(*y) not allowed!
                not isinstance(node, ast.GeneratorExp) or
                len(node.generators) != 1
            )
    ):
        yield ast_to_offset(node), _fix_seq


register(ast.ListComp)(_visit_func)
register(ast.SetComp)(_visit_func)
register(ast.GeneratorExp)(_visit_func)


def _fix_dict(i: int, tokens: list[Token]) -> None:
    comps, end = _find_comps(i, tokens)

    # need to find (whatever).items()
    #   iter_start ^         ^ iter_end
    iter_end = end - 1
    depth = 0
    while not tokens[iter_end].matches(name='OP', src='.'):
        if is_open(tokens[iter_end]):
            depth -= 1
        elif is_close(tokens[iter_end]):
            depth += 1
        iter_end -= 1

    iter_start = _and_ws_after(comps[-1].in_idx, tokens) + 1
    while depth:
        iter_start += 1
        if is_open(tokens[iter_start]):
            depth -= 1

    splatted = tokens_to_src(tokens[iter_start:iter_end])

    del_start = _and_ws_before(comps[-1].for_idx, tokens)
    end_of_elt = _and_ws_before(comps[0].for_idx, tokens)

    del tokens[del_start:end]
    tokens[i + 1:end_of_elt] = [Token('CODE', f'**{splatted}')]


@register(ast.DictComp)
def visit_DictComp(
        state: State,
        node: ast.DictComp,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            (
                state.settings.min_version >= (3, 15) or
                len(node.generators) == 1
            ) and
            isinstance(node.key, ast.Name) and
            isinstance(node.value, ast.Name) and
            not node.generators[-1].ifs and
            not node.generators[-1].is_async and
            isinstance(node.generators[-1].target, ast.Tuple) and
            len(node.generators[-1].target.elts) == 2 and
            isinstance(node.generators[-1].target.elts[0], ast.Name) and
            isinstance(node.generators[-1].target.elts[1], ast.Name) and
            node.key.id == node.generators[-1].target.elts[0].id and
            node.value.id == node.generators[-1].target.elts[1].id and
            isinstance(node.generators[-1].iter, ast.Call) and
            not node.generators[-1].iter.args and
            not node.generators[-1].iter.keywords and
            isinstance(node.generators[-1].iter.func, ast.Attribute) and
            node.generators[-1].iter.func.attr == 'items'
    ):
        yield ast_to_offset(node), _fix_dict
