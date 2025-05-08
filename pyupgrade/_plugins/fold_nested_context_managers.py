from __future__ import annotations

import ast
import functools
import itertools
from collections.abc import Iterable
from typing import Any

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import Block


def _expand_item(indent: int, item: ast.AST) -> str:
    return '{}{}'.format(' ' * indent, ast.unparse(item))


def _replace_context_managers(
    i: int,
    tokens: list[Token],
    *,
    with_items: list[ast.withitem],
    body: Iterable[ast.AST],
) -> None:
    block = Block.find(tokens, i, trim_end=True)
    block_indent = block._minimum_indent(tokens)
    replacement = '{}with ({}):\n{}\n'.format(
        ' ' * block._initial_indent(tokens),
        ', '.join(ast.unparse(item) for item in with_items),
        '\n'.join(_expand_item(block_indent, item) for item in body),
    )
    tokens[block.start:block.end] = [Token('CODE', replacement)]


def flatten(xs: Iterable[Any]) -> list[Any]:
    return list(itertools.chain.from_iterable(xs))


@register(ast.With)
def visit_With_fold_nested(
    state: State,
    node: ast.With,
    parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    """
    Fold nested with statements into one statement.

    with foo:
        with bar:
            body

    becomes

    with (foo, bar):
        body
    """
    if state.settings.min_version < (3, 10):
        return
    if isinstance(parent, ast.With):
        # The top most with statement will handle all of the children.
        return

    with_stmts = []
    current: ast.AST = node
    while isinstance(current, ast.With):
        with_stmts.append(current)
        if len(current.body) == 1:
            current = current.body[0]
        else:
            break

    if len(with_stmts) > 1:
        with_items = flatten(n.items for n in with_stmts)
        yield ast_to_offset(node), functools.partial(
            _replace_context_managers,
            body=with_stmts[-1].body,
            with_items=with_items,
        )
