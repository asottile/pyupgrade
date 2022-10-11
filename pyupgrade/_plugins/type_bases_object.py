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


def remove_base_class_from_type_call(i: int, tokens: list[Token]) -> None:
    # look forward and backward to find commas / parens
    brace_stack = []
    j = i
    while tokens[j].src != ',':
        if tokens[j].src == ')':
            brace_stack.append(j)
        j += 1
    right = j

    # if there's a close-paren after a trailing comma
    j = right + 1
    if not brace_stack and tokens[j].src != ')':
        while tokens[j].src != ')' and tokens[j].name != 'NAME':
            j += 1
        right = j

    if brace_stack:
        last_part = brace_stack[-1]
    else:  # for trailing commas
        last_part = i if tokens[i].src == ',' else i + 1

    j = i

    while tokens[j].src not in {',', '('}:
        j -= 1
    left = j

    # single base, remove the entire bases
    if tokens[left].src == '(' and tokens[right].src == ',':
        del tokens[left + 1:right + 1]
    # multiple bases, base is first
    elif tokens[left].src == '(' and tokens[right].src != ')':
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
    # multiple bases, base is not first
    else:
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
