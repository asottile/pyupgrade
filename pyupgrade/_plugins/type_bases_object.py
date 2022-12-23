from __future__ import annotations

import ast
import functools
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import UNIMPORTANT_WS

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import delete_argument


def remove_all(the_list: list[str], item: str) -> list[str]:
    return [x for x in the_list if x != item]


def remove_line(the_list: list[str], sub_list: list[str], item: str) -> list[str]:
    is_last = sub_list[-1] == item
    idx = [x.src for x in the_list].index(item)
    line = the_list[idx].line
    idxs = ([i for i, x in enumerate(the_list) if x.line == line])
    del the_list[min(idxs):max(idxs)+1]
    if is_last:
        del the_list[min(idxs)-2]


def remove_base_class_from_type_call(
    _: int, tokens: list[Token], *, arguments: list[ast.Name]
) -> None:
    print([x.src for x in tokens])
    type_start = find_open_paren(tokens, 0)
    bases_start = find_open_paren(tokens, type_start + 1)
    _, end = parse_call_args(tokens, bases_start)
    inner_tokens = tokens[bases_start + 1 : end - 1]
    last_is_comma = inner_tokens[-1].src == ','
    new_lines = [x.src for x in inner_tokens if x.name == "NL"]
    names = [x.src for x in inner_tokens if x.name == "NAME"]
    multi_line = len(new_lines) >= len(names)
    targets = ["NAME", "NL"]
    if multi_line:
        targets.remove("NL")
    inner_tokens = [x.src for x in inner_tokens if x.name in targets]
    # This gets run if the function arguments are spread out over multiple lines
    if multi_line:
        remove_line(tokens, inner_tokens, "object")
        return
    inner_tokens = remove_all(inner_tokens, "object")
    del tokens[bases_start + 1 : end - 1]
    count = 1
    object_is_last = names[-1] == "object"
    for i, token in enumerate(inner_tokens):
        # Boolean value to see if the current item is the last
        last = i == len(inner_tokens) - 1
        tokens.insert(bases_start + count, Token("NAME", token))
        count += 1
        if not last and token != "\n":
            tokens.insert(bases_start + count, Token("UNIMPORTANT_WS", " "))
            tokens.insert(bases_start + count, Token("OP", ","))
            count += 2
        elif len(inner_tokens) == 1:
            tokens.insert(bases_start + count, Token("OP", ","))
        elif last_is_comma:
            tokens.insert(bases_start + count, Token("OP", ","))


@register(ast.Call)
def visit_Call(
    state: State,
    node: ast.Call,
    parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
        isinstance(node.func, ast.Name)
        and node.func.id == "type"
        and len(node.args) > 1
        and isinstance(node.args[1], ast.Tuple)
        and any(
            isinstance(elt, ast.Name) and elt.id == "object"
            for elt in node.args[1].elts
        )
    ):
        for base in node.args[1].elts:
            if isinstance(base, ast.Name) and base.id == "object":
                # TODO: send idx of the found object
                func = functools.partial(
                    remove_base_class_from_type_call,
                    arguments=node.args[1].elts,
                )
                yield ast_to_offset(base), func
