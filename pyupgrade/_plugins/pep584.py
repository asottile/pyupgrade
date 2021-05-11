import ast
from typing import Iterable
from typing import Tuple

from tokenize_rt import List
from tokenize_rt import NON_CODING_TOKENS
from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_closing_bracket
from pyupgrade._token_helpers import find_token


def _replace_dict_brackets(i: int, tokens: List[Token]) -> None:
    closing = find_closing_bracket(tokens, i)
    j = closing - 1
    while tokens[j].name in NON_CODING_TOKENS and j > i:
        j -= 1
    if tokens[j].name == 'OP' and tokens[j].src == ',':
        tokens[j] = Token('PLACEHOLDER', '')

    if tokens[i].line == tokens[closing].line:
        tokens[i] = Token('PLACEHOLDER', '')
        tokens[closing] = Token('PLACEHOLDER', '')
    else:
        tokens[i] = Token('CODE', '(')
        tokens[closing] = Token('CODE', ')')


def _remove_double_star(i: int, tokens: List[Token]) -> None:
    j = i
    while not (tokens[j].name == 'OP' and tokens[j].src == '**'):
        j -= 1
    tokens[j] = Token('PLACEHOLDER', '')


def _replace_comma_with_pipe(i: int, tokens: List[Token]) -> None:
    comma = find_token(tokens, i, ',')
    tokens[comma] = Token('CODE', ' |')


@register(ast.Dict)
def visit_Dict(
        state: State,
        node: ast.Dict,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if state.settings.min_version < (3, 9):
        return

    if all(key is None for key in node.keys) and len(node.values) > 1:
        yield ast_to_offset(node), _replace_dict_brackets
        arg_count = len(node.values)
        for idx, arg in enumerate(node.values):
            yield ast_to_offset(arg), _remove_double_star
            if idx < arg_count - 1:
                yield ast_to_offset(arg), _replace_comma_with_pipe
