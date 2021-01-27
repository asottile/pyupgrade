import ast
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._string_helpers import is_ascii
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import replace_call


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
    if (
            state.min_version >= (3,) and
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
