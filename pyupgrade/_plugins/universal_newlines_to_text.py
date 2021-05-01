import ast
import functools
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import tokens_to_src

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args


def _replace_universal_newlines_with_text(
    i: int,
    tokens: List[Token],
    *,
    arg_idx: int,
) -> None:
    j = find_open_paren(tokens, i)
    func_args, _ = parse_call_args(tokens, j)
    src = tokens_to_src(tokens[slice(*func_args[arg_idx])])
    new_src = src.replace('universal_newlines', 'text', 1)
    tokens[slice(*func_args[arg_idx])] = [Token('SRC', new_src)]


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 7) and
            is_name_attr(
                node.func,
                state.from_imports,
                'subprocess',
                ('run',),
            )
    ):
        kwarg_idx = next(
            (
                n
                for n, keyword in enumerate(node.keywords)
                if keyword.arg == 'universal_newlines'
            ),
            None,
        )
        if kwarg_idx is not None:
            func = functools.partial(
                _replace_universal_newlines_with_text,
                arg_idx=len(node.args) + kwarg_idx,
            )
            yield ast_to_offset(node), func
