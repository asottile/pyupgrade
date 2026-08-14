from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import Block
from pyupgrade._token_helpers import find_end


def _to_lazy_imports(i: int, tokens: list[Token]) -> None:
    block = Block.find(tokens, i)

    to_insert = []
    i = block.block
    while i < block.end:
        token = tokens[i]
        if token.matches(name='NAME', src='lazy'):  # pragma: >=3.15 cover
            i = find_end(tokens, i)
        elif (
                token.matches(name='NAME', src='from') or
                token.matches(name='NAME', src='import')
        ):
            to_insert.append(i)
            i = find_end(tokens, i)
        else:
            i += 1

    block.dedent(tokens)
    for i in reversed(to_insert):
        tokens.insert(i, Token(name='CODE', src='lazy '))
    del tokens[block.start:block.block]


@register(ast.If)
def visit_If(
        state: State,
        node: ast.If,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 15) and (
                (
                    isinstance(node.test, ast.Constant) and
                    not node.test.value
                ) or
                is_name_attr(
                    node.test,
                    state.from_imports,
                    ('typing', 'typing_extensions'),
                    {'TYPE_CHECKING'},
                )
            ) and
            not node.orelse and
            all(
                isinstance(child, (ast.ImportFrom, ast.Import))
                for child in node.body
            )
    ):
        yield ast_to_offset(node), _to_lazy_imports
