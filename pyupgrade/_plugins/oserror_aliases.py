from __future__ import annotations

import ast
import functools
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import arg_str
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import replace_name

ERROR_NAMES = frozenset(('EnvironmentError', 'IOError', 'WindowsError'))
ERROR_MODULES = frozenset(('mmap', 'select', 'socket'))


def _fix_oserror_except(
        i: int,
        tokens: list[Token],
        *,
        from_imports: dict[str, set[str]],
) -> None:
    # find all the arg strs in the tuple
    except_index = i
    while tokens[except_index].src != 'except':
        except_index -= 1
    start = find_open_paren(tokens, except_index)
    func_args, end = parse_call_args(tokens, start)

    # save the exceptions and remove the block
    arg_strs = [arg_str(tokens, *arg) for arg in func_args]
    del tokens[start:end]

    # rewrite the block without dupes
    args = []
    for arg in arg_strs:
        left, part, right = arg.partition('.')
        if left in ERROR_MODULES and part == '.' and right == 'error':
            args.append('OSError')
        elif left in ERROR_NAMES and part == right == '':
            args.append('OSError')
        elif (
                left == 'error' and
                part == right == '' and
                any('error' in from_imports[mod] for mod in ERROR_MODULES)
        ):
            args.append('OSError')
        else:
            args.append(arg)

    unique_args = tuple(dict.fromkeys(args))

    if len(unique_args) > 1:
        joined = '({})'.format(', '.join(unique_args))
    elif tokens[start - 1].name != 'UNIMPORTANT_WS':
        joined = f' {unique_args[0]}'
    else:
        joined = unique_args[0]

    new = Token('CODE', joined)
    tokens.insert(start, new)


def _is_oserror_alias(
        node: ast.AST,
        from_imports: dict[str, set[str]],
) -> tuple[Offset, str] | None:
    if isinstance(node, ast.Name) and node.id in ERROR_NAMES:
        return ast_to_offset(node), node.id
    elif (
            isinstance(node, ast.Name) and
            node.id == 'error' and
            any(node.id in from_imports[mod] for mod in ERROR_MODULES)
    ):
        return ast_to_offset(node), node.id
    elif (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id in ERROR_MODULES and
            node.attr == 'error'
    ):
        return ast_to_offset(node), node.attr
    else:
        return None


def _oserror_alias_cbs(
        node: ast.AST,
        from_imports: dict[str, set[str]],
) -> Iterable[tuple[Offset, TokenFunc]]:
    offset_name = _is_oserror_alias(node, from_imports)
    if offset_name is not None:
        offset, name = offset_name
        func = functools.partial(replace_name, name=name, new='OSError')
        yield offset, func


@register(ast.Raise)
def visit_Raise(
        state: State,
        node: ast.Raise,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if node.exc is not None:
        yield from _oserror_alias_cbs(node.exc, state.from_imports)
        if isinstance(node.exc, ast.Call):
            yield from _oserror_alias_cbs(node.exc.func, state.from_imports)


@register(ast.Try)
def visit_Try(
        state: State,
        node: ast.Try,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    for handler in node.handlers:
        if (
                isinstance(handler.type, ast.Tuple) and
                any(
                    _is_oserror_alias(elt, state.from_imports)
                    for elt in handler.type.elts
                )
        ):
            func = functools.partial(
                _fix_oserror_except,
                from_imports=state.from_imports,
            )
            yield ast_to_offset(handler.type), func
        elif handler.type is not None:
            yield from _oserror_alias_cbs(handler.type, state.from_imports)
