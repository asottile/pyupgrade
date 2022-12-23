from __future__ import annotations

import ast
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args


def is_last_comma(tokens: list[Token], names: list[str]) -> bool:
    last_arg = names[-1]
    idx = [x.src for x in tokens].index(last_arg)
    return tokens[idx + 1].src == ','


def remove_all(the_list: list[str], item: str) -> list[str]:
    return [x for x in the_list if x != item]


def remove_line(
    the_list: list[Token], sub_list: list[str], item: str, last_is_comma: bool,
) -> None:
    is_last = sub_list[-1] == item
    idx = [x.src for x in the_list].index(item)
    line = the_list[idx].line
    idxs = [i for i, x in enumerate(the_list) if x.line == line]
    del the_list[min(idxs): max(idxs) + 1]
    if is_last and not last_is_comma:
        del the_list[min(idxs) - 2]


def remove_base_class_from_type_call(_: int, tokens: list[Token]) -> None:
    type_start = find_open_paren(tokens, 0)
    bases_start = find_open_paren(tokens, type_start + 1)
    _, end = parse_call_args(tokens, bases_start)
    inner_tokens = tokens[bases_start + 1: end - 1]
    new_lines = [x.src for x in inner_tokens if x.name == 'NL']
    names = [x.src for x in inner_tokens if x.name == 'NAME']
    last_is_comma = is_last_comma(tokens, names)
    multi_line = len(new_lines) >= len(names)
    targets = ['NAME', 'NL']
    if multi_line:
        targets.remove('NL')
    inner_tokens = [x.src for x in inner_tokens if x.name in targets]
    # This gets run if the function arguments are on over multiple lines
    if multi_line:
        remove_line(tokens, inner_tokens, 'object', last_is_comma)
        return
    inner_tokens = remove_all(inner_tokens, 'object')
    # start by deleting all tokens, we will selectively add back
    del tokens[bases_start + 1: end - 1]
    count = 1
    for i, token in enumerate(inner_tokens):
        # Boolean value to see if the current item is the last
        last = i == len(inner_tokens) - 1
        tokens.insert(bases_start + count, Token('NAME', token))
        count += 1
        # adds a comma and a space if the current item is not the last
        if not last and token != '\n':
            tokens.insert(bases_start + count, Token('UNIMPORTANT_WS', ' '))
            tokens.insert(bases_start + count, Token('OP', ','))
            count += 2
        # If the lenght is only one, or the last one had a comma, add a comma
        elif (last and last_is_comma) or len(inner_tokens) == 1:
            tokens.insert(bases_start + count, Token('OP', ','))


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
