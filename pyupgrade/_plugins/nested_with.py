from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import tokens_to_src

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import Block

_NEWLINES = frozenset(('NL', 'NEWLINE'))
_WITH_PREFIX_TOKENS = frozenset(('INDENT', 'UNIMPORTANT_WS'))


def _header_has_comment(tokens: list[Token], block: Block) -> bool:
    return any(
        tokens[i].name == 'COMMENT' for i in range(block.start, block.block)
    )


def _with_token_index(tokens: list[Token], block: Block) -> int:
    i = block.start
    while tokens[i].name in _WITH_PREFIX_TOKENS:
        i += 1
    return i


def _header_is_single_line(tokens: list[Token], block: Block) -> bool:
    start = _with_token_index(tokens, block)
    return all(
        tokens[i].name not in _NEWLINES
        for i in range(start, block.colon)
    )


def _item_src(tokens: list[Token], block: Block) -> str:
    i = _with_token_index(tokens, block)
    return tokens_to_src(tokens[i + 1:block.colon]).strip()


def _fix_nested_with(i: int, tokens: list[Token], item_count: int) -> None:
    blocks = [Block.find(tokens, i)]

    while (
            len(blocks) < item_count and
            (block := blocks[-1]).block + 1 < len(tokens) and
            tokens[block.block].name == 'INDENT' and
            tokens[block.block + 1].matches(name='NAME', src='with')
    ):
        blocks.append(Block.find(tokens, block.block + 1))

    if (
            len(blocks) < item_count or
            any(
                block.line or
                not _header_is_single_line(tokens, block) or
                _header_has_comment(tokens, block)
                for block in blocks
            )
    ):
        return

    indent = (
        tokens[blocks[0].start].src
        if tokens[blocks[0].start].src.isspace() else ''
    )
    newline = tokens[blocks[0].block - 1].src
    header = ''.join((
        indent, 'with (', newline,
        *(
            f'{indent}    {_item_src(tokens, block)},{newline}'
            for block in blocks
        ),
        indent, '):', newline,
    ))

    for j in range(len(blocks) - 2, -1, -1):
        blocks[j].dedent(tokens)

    for j in range(len(blocks) - 1, 0, -1):
        del tokens[blocks[j].start:blocks[j].block]

    tokens[blocks[0].start:blocks[0].block] = [Token('CODE', header)]


def _parent_wraps_with(node: ast.With, parent: ast.AST) -> bool:
    return (
        isinstance(parent, ast.With) and
        len(parent.items) == 1 and
        len(parent.body) == 1 and
        parent.body[0] is node
    )


def _single_line_item(item: ast.withitem) -> bool:
    return (
        item.context_expr.end_lineno is not None and
        item.context_expr.lineno == item.context_expr.end_lineno and
        (
            item.optional_vars is None or (
                item.optional_vars.end_lineno is not None and
                item.optional_vars.lineno == item.optional_vars.end_lineno
            )
        )
    )


@register(ast.With)
def visit_With(
        state: State,
        node: ast.With,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version < (3, 10) or
            _parent_wraps_with(node, parent)
    ):
        return

    cur = node
    item_count = 1
    while (
            len(cur.items) == 1 and
            _single_line_item(cur.items[0]) and
            len(cur.body) == 1 and
            isinstance((nxt := cur.body[0]), ast.With)
    ):
        cur = nxt
        item_count += 1

    if item_count < 2:
        return

    yield ast_to_offset(node), (
        lambda i, tokens: _fix_nested_with(i, tokens, item_count)
    )
