import ast
import functools
import sys
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import CLOSING
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_token
from pyupgrade._token_helpers import OPENING


def _fix_optional(i: int, tokens: List[Token]) -> None:
    j = find_token(tokens, i, '[')
    k = find_closing_bracket(tokens, j)
    if tokens[j].line == tokens[k].line:
        tokens[k] = Token('CODE', ' | None')
        del tokens[i:j + 1]
    else:
        tokens[j] = tokens[j]._replace(src='(')
        tokens[k] = tokens[k]._replace(src=')')
        tokens[i:j] = [Token('CODE', 'None | ')]


def _fix_union(
        i: int,
        tokens: List[Token],
        *,
        arg: ast.expr,
        arg_count: int,
) -> None:
    arg_offset = ast_to_offset(arg)
    j = find_token(tokens, i, '[')
    to_delete = []
    commas: List[int] = []

    arg_depth = -1
    depth = 1
    k = j + 1
    while depth:
        if tokens[k].src in OPENING:
            if arg_depth == -1:
                to_delete.append(k)
            depth += 1
        elif tokens[k].src in CLOSING:
            depth -= 1
            if 0 < depth < arg_depth:
                to_delete.append(k)
        elif tokens[k].offset == arg_offset:
            arg_depth = depth
        elif depth == arg_depth and tokens[k].src == ',':
            if len(commas) >= arg_count - 1:
                to_delete.append(k)
            else:
                commas.append(k)

        k += 1
    k -= 1

    if tokens[j].line == tokens[k].line:
        del tokens[k]
        for comma in commas:
            tokens[comma] = Token('CODE', ' |')
        for paren in reversed(to_delete):
            del tokens[paren]
        del tokens[i:j + 1]
    else:
        tokens[j] = tokens[j]._replace(src='(')
        tokens[k] = tokens[k]._replace(src=')')

        for comma in commas:
            tokens[comma] = Token('CODE', ' |')
        for paren in reversed(to_delete):
            del tokens[paren]
        del tokens[i:j]


def _supported_version(state: State) -> bool:
    return (
        state.in_annotation and (
            state.settings.min_version >= (3, 10) or
            'annotations' in state.from_imports['__future__']
        )
    )


@register(ast.Subscript)
def visit_Subscript(
        state: State,
        node: ast.Subscript,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if not _supported_version(state):
        return

    if is_name_attr(node.value, state.from_imports, 'typing', ('Optional',)):
        yield ast_to_offset(node), _fix_optional
    elif is_name_attr(node.value, state.from_imports, 'typing', ('Union',)):
        if sys.version_info >= (3, 9):  # pragma: no cover (py39+)
            node_slice: ast.expr = node.slice
        elif isinstance(node.slice, ast.Index):  # pragma: no cover (<py39)
            node_slice = node.slice.value
        else:  # pragma: no cover (<py39)
            return  # unexpected slice type

        if isinstance(node_slice, ast.Tuple):
            if node_slice.elts:
                arg = node_slice.elts[0]
                arg_count = len(node_slice.elts)
            else:
                return  # empty Union
        else:
            arg = node_slice
            arg_count = 1

        func = functools.partial(_fix_union, arg=arg, arg_count=arg_count)
        yield ast_to_offset(node), func
