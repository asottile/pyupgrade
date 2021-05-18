import ast
import sys
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket


def _replace_list_comprehension(i: int, tokens: List[Token]) -> None:
    if sys.version_info < (3, 8):  # pragma: no cover (py38+)
        start = i - 1
        while not (tokens[start].name == 'OP' and tokens[start].src == '['):
            start -= 1
    else:  # pragma: no cover (<py38)
        start = i
    j = find_closing_bracket(tokens, start)
    tokens[start] = tokens[start]._replace(src='(')
    tokens[j] = tokens[j]._replace(src=')')


@register(ast.Assign)
def visit_Assign(
        state: State,
        node: ast.Assign,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            len(node.targets) == 1 and
            isinstance(node.targets[0], ast.Tuple) and
            isinstance(node.value, ast.ListComp)
    ):
        yield ast_to_offset(node.value), _replace_list_comprehension
