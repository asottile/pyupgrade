import ast
import functools
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Union

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc

LITERAL_TYPES = (ast.Str, ast.Num, ast.Bytes)


def _fix_is_literal(
        i: int,
        tokens: List[Token],
        *,
        op: Union[ast.Is, ast.IsNot],
) -> None:
    while tokens[i].src != 'is':
        i -= 1
    if isinstance(op, ast.Is):
        tokens[i] = tokens[i]._replace(src='==')
    else:
        tokens[i] = tokens[i]._replace(src='!=')
        # since we iterate backward, the empty tokens keep the same length
        i += 1
        while tokens[i].src != 'not':
            tokens[i] = Token('EMPTY', '')
            i += 1
        tokens[i] = Token('EMPTY', '')


@register(ast.Compare)
def visit_Compare(
        state: State,
        node: ast.Compare,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    left = node.left
    for op, right in zip(node.ops, node.comparators):
        if (
                isinstance(op, (ast.Is, ast.IsNot)) and
                (
                    isinstance(left, LITERAL_TYPES) or
                    isinstance(right, LITERAL_TYPES)
                )
        ):
            func = functools.partial(_fix_is_literal, op=op)
            yield ast_to_offset(right), func
        left = right
