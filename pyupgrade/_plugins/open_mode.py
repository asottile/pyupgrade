import ast
from typing import Iterable
from typing import List
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token
from tokenize_rt import tokens_to_src

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args

U_MODE_REMOVE = frozenset(('U', 'Ur', 'rU', 'r', 'rt', 'tr'))
U_MODE_REPLACE_R = frozenset(('Ub', 'bU'))
U_MODE_REMOVE_U = frozenset(('rUb', 'Urb', 'rbU', 'Ubr', 'bUr', 'brU'))
U_MODE_REPLACE = U_MODE_REPLACE_R | U_MODE_REMOVE_U


def _fix_open_mode(i: int, tokens: List[Token]) -> None:
    j = find_open_paren(tokens, i)
    func_args, end = parse_call_args(tokens, j)
    mode = tokens_to_src(tokens[slice(*func_args[1])])
    mode_stripped = mode.strip().strip('"\'')
    if mode_stripped in U_MODE_REMOVE:
        del tokens[func_args[0][1]:func_args[1][1]]
    elif mode_stripped in U_MODE_REPLACE_R:
        new_mode = mode.replace('U', 'r')
        tokens[slice(*func_args[1])] = [Token('SRC', new_mode)]
    elif mode_stripped in U_MODE_REMOVE_U:
        new_mode = mode.replace('U', '')
        tokens[slice(*func_args[1])] = [Token('SRC', new_mode)]
    else:
        raise AssertionError(f'unreachable: {mode!r}')


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            isinstance(node.func, ast.Name) and
            node.func.id == 'open' and
            not has_starargs(node) and
            len(node.args) >= 2 and
            isinstance(node.args[1], ast.Str) and (
                node.args[1].s in U_MODE_REPLACE or
                (len(node.args) == 2 and node.args[1].s in U_MODE_REMOVE)
            )
    ):
        yield ast_to_offset(node), _fix_open_mode
