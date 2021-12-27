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
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_open_paren


def _remove_abspath(i: int, tokens: List[Token]) -> None:
    paren_start = find_open_paren(tokens, i + 1)
    paren_end = find_closing_bracket(tokens, paren_start)
    while i <= paren_start:
        tokens[i] = Token('PLACEHOLDER', '')
        i += 1
    tokens[paren_end] = Token('PLACEHOLDER', '')


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3, 9) and
            (
                (
                    isinstance(node.func, ast.Name) and
                    node.func.id == 'abspath' and
                    node.func.id in state.from_imports['os.path']
                ) or
                (
                    isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Attribute) and
                    isinstance(node.func.value.value, ast.Name) and
                    node.func.value.value.id == 'os' and
                    node.func.value.attr == 'path' and
                    node.func.attr == 'abspath'
                )
            ) and
            len(node.args) == 1 and
            isinstance(node.args[0], ast.Name) and
            node.args[0].id == '__file__'
    ):
        yield ast_to_offset(node), _remove_abspath
