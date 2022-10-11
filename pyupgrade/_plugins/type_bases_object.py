from __future__ import annotations

import ast
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


def remove_base_class_from_type_call(i: int, tokens: list[Token]) -> None:
    type_start = find_open_paren(tokens, 0)
    bases_start = find_open_paren(tokens, type_start + 1)
    bases, end = parse_call_args(tokens, bases_start)
    for base_start, base_end in bases:
        for token in tokens[base_start:base_end]:
            if token.src == 'object':
                object_index = bases.index((base_start, base_end))
                # handle object first
                if object_index == 0:
                    # (object, tuple[,]) -> (tuple,)
                    if len(bases) == 2:
                        tokens.insert(bases[1][1], Token('OP', ','))
                    # (object, foo, bar, ...[,]) -> (foo, bar, ...[,])
                    if len(bases) >= 2:
                        next_arg_start = bases[1][0]
                        # preserve newlines
                        if tokens[next_arg_start].name == 'NL':
                            del tokens[base_start:next_arg_start]
                        else:
                            del tokens[base_start:bases[1][0] + 1]
                    # (object,) -> ()
                    else:
                        del tokens[base_start:base_end + 1]
                # handle object last
                elif object_index == len(bases) - 1:
                    # (tuple, object[,]) -> (tuple,)
                    if len(bases) == 2:
                        del tokens[base_start:base_end]
                    # (foo, bar, ..., object[,]) -> (foo, bar, ...[,])
                    else:
                        if tokens[base_end - 1].name == UNIMPORTANT_WS and \
                                tokens[base_end - 2].name == 'NL':
                            del tokens[base_start - 1:base_end - 2]
                        else:
                            del tokens[base_start - 1:base_end]
                # handle object in the middle
                else:
                    del tokens[base_start:base_end + 1]
                return


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
