from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import Block
from pyupgrade._version_expr import always_false
from pyupgrade._version_expr import always_true
from pyupgrade._version_expr import norm_min_version


def _find_if_else_block(tokens: list[Token], i: int) -> tuple[Block, Block]:
    if_block = Block.find(tokens, i)
    i = if_block.end
    while tokens[i].src != 'else':
        i += 1
    else_block = Block.find(tokens, i, trim_end=True)
    return if_block, else_block


def _fix_py3_block(i: int, tokens: list[Token]) -> None:
    if tokens[i].src == 'if':
        if_block = Block.find(tokens, i)
        if_block.dedent(tokens)
        del tokens[if_block.start:if_block.block]
    else:
        if_block = Block.find(tokens, i)
        if_block.replace_condition(tokens, [Token('NAME', 'else')])


def _fix_py2_block(i: int, tokens: list[Token]) -> None:
    if tokens[i].src == 'if':
        if_block, else_block = _find_if_else_block(tokens, i)
        else_block.dedent(tokens)
        del tokens[if_block.start:else_block.block]
    else:
        if_block, else_block = _find_if_else_block(tokens, i)
        del tokens[if_block.start:else_block.start]


def _fix_remove_block(i: int, tokens: list[Token]) -> None:
    block = Block.find(tokens, i)
    del tokens[block.start:block.end]


def _fix_py2_convert_elif(i: int, tokens: list[Token]) -> None:
    if_block = Block.find(tokens, i)
    # wasn't actually followed by an `elif`
    if tokens[if_block.end].src != 'elif':
        return
    tokens[if_block.end] = Token('CODE', tokens[i].src)
    _fix_remove_block(i, tokens)


def _fix_py3_block_else(i: int, tokens: list[Token]) -> None:
    if tokens[i].src == 'if':
        if_block, else_block = _find_if_else_block(tokens, i)
        if_block.dedent(tokens)
        del tokens[if_block.end:else_block.end]
        del tokens[if_block.start:if_block.block]
    else:
        if_block, else_block = _find_if_else_block(tokens, i)
        del tokens[if_block.end:else_block.end]
        if_block.replace_condition(tokens, [Token('NAME', 'else')])


def _fix_py3_convert_elif(i: int, tokens: list[Token]) -> None:
    if_block = Block.find(tokens, i)
    # wasn't actually followed by an `elif`
    if tokens[if_block.end].src != 'elif':
        return
    tokens[if_block.end] = Token('CODE', tokens[i].src)
    if_block.dedent(tokens)
    del tokens[if_block.start:if_block.block]


@register(ast.If)
def visit_If(
        state: State,
        node: ast.If,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    min_version = norm_min_version(state.settings.min_version)

    if always_false(node.test, state, min_version):
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            yield ast_to_offset(node), _fix_py2_convert_elif
        elif node.orelse:
            yield ast_to_offset(node), _fix_py2_block
        elif node.col_offset == 0:
            yield ast_to_offset(node), _fix_remove_block
    elif always_true(node.test, state, min_version):
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            yield ast_to_offset(node), _fix_py3_convert_elif
        elif node.orelse:
            yield ast_to_offset(node), _fix_py3_block_else
        else:
            yield ast_to_offset(node), _fix_py3_block
