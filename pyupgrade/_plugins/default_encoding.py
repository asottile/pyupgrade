import ast
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._string_helpers import is_codec
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_open_paren


def _fix_default_encoding(i: int, tokens: List[Token]) -> None:
    i = find_open_paren(tokens, i + 1)
    j = find_closing_bracket(tokens, i)
    del tokens[i + 1:j]


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, (ast.Str, ast.JoinedStr)) and
            node.func.attr == 'encode' and
            not has_starargs(node) and
            len(node.args) == 1 and
            isinstance(node.args[0], ast.Str) and
            is_codec(node.args[0].s, 'utf-8')
    ):
        yield ast_to_offset(node), _fix_default_encoding
