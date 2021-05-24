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
from pyupgrade._token_helpers import find_comprehension_opening_bracket


ALLOWED_FUNCS = frozenset((
    'bytearray',
    'bytes',
    'frozenset',
    'list',
    'max',
    'min',
    'sorted',
    'sum',
    'tuple',
))


def _delete_list_comp_brackets(i: int, tokens: List[Token]) -> None:
    start = find_comprehension_opening_bracket(i, tokens)
    end = find_closing_bracket(tokens, start)
    tokens[end] = Token('PLACEHOLDER', '')
    tokens[start] = Token('PLACEHOLDER', '')


def _replace_list_comp_brackets(i: int, tokens: List[Token]) -> None:
    start = find_comprehension_opening_bracket(i, tokens)
    end = find_closing_bracket(tokens, start)
    tokens[end] = Token('OP', ')')
    tokens[start] = Token('OP', '(')


def _func_condition(func: ast.expr) -> bool:
    return (
        (
            isinstance(func, ast.Name) and
            func.id in ALLOWED_FUNCS
        ) or
        (
            isinstance(func, ast.Attribute) and
            isinstance(func.value, ast.Str) and
            func.attr == 'join'
        )
    )


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            _func_condition(node.func) and
            node.args and
            isinstance(node.args[0], ast.ListComp)
    ):
        if len(node.args) == 1 and not node.keywords:
            yield ast_to_offset(node.args[0]), _delete_list_comp_brackets
        else:
            yield ast_to_offset(node.args[0]), _replace_list_comp_brackets
