import ast
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import NON_CODING_TOKENS
from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_async_listcomp
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_comprehension_opening_bracket
from pyupgrade._token_helpers import replace_list_comp_brackets


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
    j = end + 1
    while j < len(tokens) and tokens[j].name in NON_CODING_TOKENS:
        j += 1
    if tokens[j].name == 'OP' and tokens[j].src == ',':
        tokens[j] = Token('PLACEHOLDER', '')


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            isinstance(node.func, ast.Name) and
            node.func.id in ALLOWED_FUNCS and
            node.args and
            isinstance(node.args[0], ast.ListComp) and
            not is_async_listcomp(node.args[0])
    ):
        if len(node.args) == 1 and not node.keywords:
            yield ast_to_offset(node.args[0]), _delete_list_comp_brackets
        else:
            yield ast_to_offset(node.args[0]), replace_list_comp_brackets
