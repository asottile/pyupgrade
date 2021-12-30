import ast
import functools
import sys
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Type

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._string_helpers import is_ascii
from pyupgrade._token_helpers import find_and_replace_call
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import replace_call

_EXPR_NEEDS_PARENS: Tuple[Type[ast.expr], ...] = (
    ast.Await, ast.BinOp, ast.BoolOp, ast.Compare, ast.GeneratorExp, ast.IfExp,
    ast.Lambda, ast.UnaryOp,
)
if sys.version_info >= (3, 8):  # pragma: >=3.8 cover
    _EXPR_NEEDS_PARENS += (ast.NamedExpr,)

SIX_CALLS = {
    'u': '{args[0]}',
    'byte2int': '{args[0]}[0]',
    'indexbytes': '{args[0]}[{rest}]',
    'iteritems': '{args[0]}.items()',
    'iterkeys': '{args[0]}.keys()',
    'itervalues': '{args[0]}.values()',
    'viewitems': '{args[0]}.items()',
    'viewkeys': '{args[0]}.keys()',
    'viewvalues': '{args[0]}.values()',
    'create_unbound_method': '{args[0]}',
    'get_unbound_function': '{args[0]}',
    'get_method_function': '{args[0]}.__func__',
    'get_method_self': '{args[0]}.__self__',
    'get_function_closure': '{args[0]}.__closure__',
    'get_function_code': '{args[0]}.__code__',
    'get_function_defaults': '{args[0]}.__defaults__',
    'get_function_globals': '{args[0]}.__globals__',
    'assertCountEqual': '{args[0]}.assertCountEqual({rest})',
    'assertRaisesRegex': '{args[0]}.assertRaisesRegex({rest})',
    'assertRegex': '{args[0]}.assertRegex({rest})',
}
SIX_INT2BYTE_TMPL = 'bytes(({args[0]},))'
RAISE_FROM_TMPL = 'raise {args[0]} from {args[1]}'
RERAISE_TMPL = 'raise'
RERAISE_2_TMPL = 'raise {args[1]}.with_traceback(None)'
RERAISE_3_TMPL = 'raise {args[1]}.with_traceback({args[2]})'


def _fix_six_b(i: int, tokens: List[Token]) -> None:
    j = find_open_paren(tokens, i)
    if (
            tokens[j + 1].name == 'STRING' and
            is_ascii(tokens[j + 1].src) and
            tokens[j + 2].src == ')'
    ):
        func_args, end = parse_call_args(tokens, j)
        replace_call(tokens, i, end, func_args, 'b{args[0]}')


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if state.settings.min_version < (3,):
        return

    if isinstance(node.func, ast.Name):
        name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        name = node.func.attr
    else:
        return

    if (
            is_name_attr(
                node.func,
                state.from_imports,
                'six',
                ('iteritems', 'iterkeys', 'itervalues'),
            ) and
            node.args and
            not has_starargs(node) and
            # parent is next(...)
            isinstance(parent, ast.Call) and
            isinstance(parent.func, ast.Name) and
            parent.func.id == 'next'
    ):
        func = functools.partial(
            find_and_replace_call,
            template=f'iter({SIX_CALLS[name]})',
        )
        yield ast_to_offset(node), func
    elif (
            is_name_attr(node.func, state.from_imports, 'six', SIX_CALLS) and
            node.args and
            not has_starargs(node)
    ):
        if isinstance(node.args[0], _EXPR_NEEDS_PARENS):
            parens: Tuple[int, ...] = (0,)
        else:
            parens = ()
        func = functools.partial(
            find_and_replace_call,
            template=SIX_CALLS[name],
            parens=parens,
        )
        yield ast_to_offset(node), func
    elif (
            is_name_attr(
                node.func,
                state.from_imports,
                'six',
                ('int2byte',),
            ) and
            node.args and
            not has_starargs(node)
    ):
        func = functools.partial(
            find_and_replace_call,
            template=SIX_INT2BYTE_TMPL,
        )
        yield ast_to_offset(node), func
    elif (
            state.settings.min_version >= (3,) and
            is_name_attr(
                node.func,
                state.from_imports,
                'six',
                ('b', 'ensure_binary'),
            ) and
            not node.keywords and
            not has_starargs(node) and
            len(node.args) == 1 and
            isinstance(node.args[0], ast.Str)
    ):
        yield ast_to_offset(node), _fix_six_b
    elif (
            isinstance(parent, ast.Expr) and
            is_name_attr(
                node.func,
                state.from_imports,
                'six',
                ('raise_from',),
            ) and
            node.args and
            not has_starargs(node)
    ):
        func = functools.partial(
            find_and_replace_call,
            template=RAISE_FROM_TMPL,
        )
        yield ast_to_offset(node), func
    elif (
            isinstance(parent, ast.Expr) and
            is_name_attr(
                node.func,
                state.from_imports,
                'six',
                ('reraise',),
            )
    ):
        if (
                len(node.args) == 2 and
                not node.keywords and
                not has_starargs(node)
        ):
            func = functools.partial(
                find_and_replace_call,
                template=RERAISE_2_TMPL,
            )
            yield ast_to_offset(node), func
        elif (
                len(node.args) == 3 and
                not node.keywords and
                not has_starargs(node)
        ):
            func = functools.partial(
                find_and_replace_call,
                template=RERAISE_3_TMPL,
            )
            yield ast_to_offset(node), func
        elif (
                len(node.args) == 1 and
                not node.keywords and
                isinstance(node.args[0], ast.Starred) and
                isinstance(node.args[0].value, ast.Call) and
                is_name_attr(
                    node.args[0].value.func,
                    state.from_imports,
                    'sys',
                    ('exc_info',),
                )
        ):
            func = functools.partial(
                find_and_replace_call,
                template=RERAISE_TMPL,
            )
            yield ast_to_offset(node), func
