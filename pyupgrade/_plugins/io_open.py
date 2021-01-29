import ast
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren


def _replace_io_open(i: int, tokens: List[Token]) -> None:
    j = find_open_paren(tokens, i)
    tokens[i:j] = [tokens[i]._replace(name='NAME', src='open')]


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'io' and
            node.func.attr == 'open'
    ):
        yield ast_to_offset(node.func), _replace_io_open
