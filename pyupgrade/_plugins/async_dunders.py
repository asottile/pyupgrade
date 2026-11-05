from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_op
from pyupgrade._token_helpers import is_close
from pyupgrade._token_helpers import is_open

_DUNDER_TO_BUILTIN = {
    '__aiter__': 'aiter',
    '__anext__': 'anext',
}


def _find_op_backward(tokens: list[Token], i: int, src: str) -> int:
    while not tokens[i].matches(name='OP', src=src):
        i -= 1
    return i


def _find_name_no_nested(tokens: list[Token], i: int, dunder: str) -> int:
    depth = 0
    while depth or not tokens[i].matches(name='NAME', src=dunder):
        if is_open(tokens[i]):
            depth += 1
        elif is_close(tokens[i]):
            depth -= 1
        i += 1
    return i


def _fix(i: int, tokens: list[Token], *, dunder: str) -> None:
    # Remove dunder.
    dunder_i = _find_name_no_nested(tokens, i, dunder)
    attr = _find_op_backward(tokens, dunder_i, '.')
    call = find_op(tokens, dunder_i, '(')
    call_end = find_op(tokens, call, ')')
    del tokens[attr:call_end + 1]

    # Use builtin.
    tokens.insert(attr, Token('CODE', ')'))
    call_name = _DUNDER_TO_BUILTIN[dunder]
    tokens.insert(i, Token('CODE', f"{call_name}("))


_visited_nodes: set[ast.Call] = set()


def _is_dunder_call(node: ast.Call) -> bool:
    return (
        not node.args and
        not node.keywords and
        isinstance(node.func, ast.Attribute) and
        node.func.attr in _DUNDER_TO_BUILTIN
    )


def _walk_trailing_nodes(node: ast.expr) -> Iterable[ast.Call]:
    while True:
        if isinstance(node, ast.Call):
            # a.__aiter__().__anext__()
            if _is_dunder_call(node):
                yield node
            # a.__aiter__().something().__anext__()
            node = node.func
        elif isinstance(node, ast.Attribute):
            # a.__aiter__().something.__anext__()
            node = node.value
        elif isinstance(node, ast.Subscript):
            # a.__aiter__().something[x].__anext__()
            node = node.value
        else:
            return


@register(ast.Module)
def visit_Module(
        state: State,
        node: ast.Module,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    _visited_nodes.clear()
    return
    yield


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 10) and
            _is_dunder_call(node) and
            node not in _visited_nodes
    ):
        # By default pyupgrade applies fixes in the order nodes are visited.
        # So in `a.__aiter__().__anext__()` the `anext` fix is applied first
        # before `aiter`, resulting in incorrect `aiter(anext(a))`.
        # To define correct order of fixes, we walk the whole chain
        # to gather all fixes first, so they can be applied in reversed order.
        dunder_calls = list(_walk_trailing_nodes(node))
        _visited_nodes.update(dunder_calls)

        for call in reversed(dunder_calls):
            assert isinstance(call.func, ast.Attribute)
            func = functools.partial(_fix, dunder=call.func.attr)
            yield ast_to_offset(call), func
