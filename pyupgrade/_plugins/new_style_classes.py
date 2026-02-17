from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_op
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import remove_base_class


def _fix_type_call_bases(
        i: int,
        tokens: list[Token],
        *,
        arg_count: int,
) -> None:
    j = find_op(tokens, i, '(')
    func_args, end = parse_call_args(tokens, j)
    # func_args[1] is the second argument (bases tuple)
    bases_start, bases_end = func_args[1]

    # find the ( and ) of the bases tuple
    k = bases_start
    while tokens[k].src != '(':
        k += 1
    paren_start = k

    k = bases_end - 1
    while tokens[k].src != ')':
        k -= 1
    paren_end = k

    if arg_count == 1:
        # single base (object,) -> ()
        tokens[paren_start + 1:paren_end] = []
    else:
        # multiple bases -- remove each `object` and its comma
        # rebuild the tuple contents without `object`
        inner_args, _ = parse_call_args(tokens, paren_start)
        new_parts = []
        for arg_start, arg_end in inner_args:
            src = ''.join(t.src for t in tokens[arg_start:arg_end]).strip()
            if src != 'object':
                new_parts.append(src)

        if new_parts:
            new_inner = ', '.join(new_parts)
            if len(new_parts) == 1:
                new_inner += ','
            tokens[paren_start + 1:paren_end] = [Token('CODE', new_inner)]


@register(ast.ClassDef)
def visit_ClassDef(
        state: State,
        node: ast.ClassDef,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == 'object':
            yield ast_to_offset(base), remove_base_class


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            isinstance(node.func, ast.Name) and
            node.func.id == 'type' and
            len(node.args) == 3 and
            not node.keywords and
            not has_starargs(node) and
            isinstance(node.args[1], ast.Tuple) and
            any(
                isinstance(elt, ast.Name) and elt.id == 'object'
                for elt in node.args[1].elts
            )
    ):
        object_count = sum(
            1 for elt in node.args[1].elts
            if isinstance(elt, ast.Name) and elt.id == 'object'
        )
        non_object_count = len(node.args[1].elts) - object_count
        if non_object_count == 0:
            # all bases are object -- replace with empty tuple
            func = functools.partial(
                _fix_type_call_bases,
                arg_count=1,
            )
        else:
            func = functools.partial(
                _fix_type_call_bases,
                arg_count=len(node.args[1].elts),
            )
        yield ast_to_offset(node), func
