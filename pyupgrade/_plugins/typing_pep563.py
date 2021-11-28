import ast
import functools
import sys
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from tokenize_rt import Offset

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import Token
from pyupgrade._data import TokenFunc


def _supported_version(state: State) -> bool:
    return (
        state.settings.min_version >= (3, 11) or
        'annotations' in state.from_imports['__future__']
    )


def _dequote(i: int, tokens: List[Token], *, new: str) -> None:
    tokens[i] = tokens[i]._replace(src=new)


def _get_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    else:
        raise AssertionError(f'expected Name or Attribute: {ast.dump(node)}')


def _get_keyword_value(
        keywords: List[ast.keyword],
        keyword: str,
) -> Optional[ast.expr]:
    for kw in keywords:
        if kw.arg == keyword:
            return kw.value
    else:
        return None


def _process_call(node: ast.Call) -> Iterable[ast.AST]:
    name = _get_name(node.func)
    args = node.args
    keywords = node.keywords
    if name == 'TypedDict':
        if keywords:
            for keyword in keywords:
                yield keyword.value
        elif len(args) != 2:  # garbage
            pass
        elif isinstance(args[1], ast.Dict):
            yield from args[1].values
        else:
            raise AssertionError(f'expected ast.Dict: {ast.dump(args[1])}')
    elif name == 'NamedTuple':
        if len(args) == 2:
            fields: Optional[ast.expr] = args[1]
        elif keywords:
            fields = _get_keyword_value(keywords, 'fields')
        else:  # garbage
            fields = None

        if isinstance(fields, ast.List):
            for elt in fields.elts:
                if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                    yield elt.elts[1]
        elif fields is not None:
            raise AssertionError(f'expected ast.List: {ast.dump(fields)}')
    elif name in {
        'Arg',
        'DefaultArg',
        'NamedArg',
        'DefaultNamedArg',
        'VarArg',
        'KwArg',
    }:
        if args:
            yield args[0]
        else:
            keyword_value = _get_keyword_value(keywords, 'type')
            if keyword_value is not None:
                yield keyword_value


def _process_subscript(node: ast.Subscript) -> Iterable[ast.AST]:
    name = _get_name(node.value)
    if name == 'Annotated':
        if sys.version_info >= (3, 9):  # pragma: >=3.9 cover
            node_slice = node.slice
        elif isinstance(node.slice, ast.Index):  # pragma: <3.9 cover
            node_slice: ast.AST = node.slice.value
        else:  # pragma: <3.9 cover
            node_slice = node.slice

        if isinstance(node_slice, ast.Tuple) and node_slice.elts:
            yield node_slice.elts[0]
    elif name != 'Literal':
        yield node.slice


def _replace_string_literal(
        annotation: ast.expr,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    nodes: List[ast.AST] = [annotation]
    while nodes:
        node = nodes.pop()
        if isinstance(node, ast.Call):
            nodes.extend(_process_call(node))
        elif isinstance(node, ast.Subscript):
            nodes.extend(_process_subscript(node))
        elif isinstance(node, ast.Str):
            func = functools.partial(_dequote, new=node.s)
            yield ast_to_offset(node), func
        else:
            for name in node._fields:
                value = getattr(node, name)
                if isinstance(value, ast.AST):
                    nodes.append(value)
                elif isinstance(value, list):
                    nodes.extend(value)


def _process_args(
        args: Sequence[Optional[ast.arg]],
) -> Iterable[Tuple[Offset, TokenFunc]]:
    for arg in args:
        if arg is not None and arg.annotation is not None:
            yield from _replace_string_literal(arg.annotation)


@register(ast.FunctionDef)
def visit_FunctionDef(
        state: State,
        node: ast.FunctionDef,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if not _supported_version(state):
        return

    yield from _process_args([node.args.vararg, node.args.kwarg])
    yield from _process_args(node.args.args)
    yield from _process_args(node.args.kwonlyargs)
    yield from _process_args(getattr(node.args, 'posonlyargs', []))
    if node.returns is not None:
        yield from _replace_string_literal(node.returns)


@register(ast.AnnAssign)
def visit_AnnAssign(
        state: State,
        node: ast.AnnAssign,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if not _supported_version(state):
        return
    yield from _replace_string_literal(node.annotation)
