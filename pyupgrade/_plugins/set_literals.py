import ast
import functools
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import BRACES
from pyupgrade._token_helpers import immediately_paren
from pyupgrade._token_helpers import remove_brace
from pyupgrade._token_helpers import victims

SET_TRANSFORM = (ast.List, ast.ListComp, ast.GeneratorExp, ast.Tuple)


def _fix_set_empty_literal(i: int, tokens: List[Token]) -> None:
    # TODO: this could be implemented with a little extra logic
    if not immediately_paren('set', tokens, i):
        return

    j = i + 2
    brace_stack = ['(']
    while brace_stack:
        token = tokens[j].src
        if token == BRACES[brace_stack[-1]]:
            brace_stack.pop()
        elif token in BRACES:
            brace_stack.append(token)
        elif '\n' in token:
            # Contains a newline, could cause a SyntaxError, bail
            return
        j += 1

    # Remove the inner tokens
    del tokens[i + 2:j - 1]


def _fix_set_literal(i: int, tokens: List[Token], *, arg: ast.expr) -> None:
    # TODO: this could be implemented with a little extra logic
    if not immediately_paren('set', tokens, i):
        return

    gen = isinstance(arg, ast.GeneratorExp)
    set_victims = victims(tokens, i + 1, arg, gen=gen)

    del set_victims.starts[0]
    end_index = set_victims.ends.pop()

    tokens[end_index] = Token('OP', '}')
    for index in reversed(set_victims.starts + set_victims.ends):
        remove_brace(tokens, index)
    tokens[i:i + 2] = [Token('OP', '{')]


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            isinstance(node.func, ast.Name) and
            node.func.id == 'set' and
            len(node.args) == 1 and
            not node.keywords and
            isinstance(node.args[0], SET_TRANSFORM)
    ):
        arg, = node.args
        if isinstance(arg, (ast.List, ast.Tuple)) and not arg.elts:
            yield ast_to_offset(node.func), _fix_set_empty_literal
        else:
            func = functools.partial(_fix_set_literal, arg=arg)
            yield ast_to_offset(node.func), func
