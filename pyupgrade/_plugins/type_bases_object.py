from __future__ import annotations

import ast
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import remove_base_class


def _should_move_right_edge(src: str) -> bool:
    return src != ')'


def _not_right_edge(token: Token) -> bool:
    return token.src != ')' and token.name != 'NAME'


def _last_part_function(i: int, src: str) -> int:
    return i if src == ',' else i + 1


def _remove_bases(tokens: list[Token], left: int, right: int) -> None:
    del tokens[left + 1:right + 1]


def _multiple_first(tokens: list[Token], left: int, right: int) -> None:
    # only one base will be left, (tuple) -> (tuple,)
    if sum(
            1 if token.name == 'NAME' else 0
            for token in tokens[left:find_closing_bracket(tokens, left)]
    ) == 2:
        tokens.insert(right + 1, Token('OP', ','))
    # we should preserve the newline
    if tokens[left + 1].name == 'NL':
        # we should also preserve indents
        if tokens[left + 2].name == 'UNIMPORTANT_WS':
            del tokens[left + 3:right]
        else:
            del tokens[left + 2:right]
    else:
        del tokens[left + 1:right]


def _multiple_last(tokens: list[Token], left: int, last_part: int) -> None:
    type_call_open = find_open_paren(tokens, 0)
    bases_open = find_open_paren(tokens, type_call_open + 1)
    # only one base will be left, (tuple) -> (tuple,)
    if sum(
            1 if token.name == 'NAME' else 0
            for token in tokens[bases_open:last_part + 1]
    ) == 2:
        del tokens[left + 1:last_part]
    # we should preserve indents
    elif tokens[last_part - 1].name == 'UNIMPORTANT_WS':
        # we should also preserve the newline
        if tokens[last_part - 2].name == 'NL':
            del tokens[left:last_part - 2]
        else:
            del tokens[left:last_part - 1]
    else:
        del tokens[left:last_part]


def remove_base_class_from_type_call(i: int, tokens: list[Token]) -> None:
    remove_base_class(
        i,
        tokens,
        should_move_right_edge=_should_move_right_edge,
        not_right_edge=_not_right_edge,
        last_part_function=_last_part_function,
        do_brace_stack_pop_loop=False,
        remove_bases=_remove_bases,
        single_base_char=',',
        multiple_first_char=')',
        multiple_first=_multiple_first,
        multiple_last=_multiple_last,
    )


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
        isinstance(node.func, ast.Name) and
        node.func.id == 'type' and
        len(node.args) > 1 and
        isinstance(node.args[1], ast.Tuple) and
        any(
            isinstance(elt, ast.Name) and elt.id == 'object'
            for elt in node.args[1].elts
        )
    ):
        for base in node.args[1].elts:
            if isinstance(base, ast.Name) and base.id == 'object':
                yield ast_to_offset(base), remove_base_class_from_type_call
