import ast
from typing import Dict
from typing import Iterable
from typing import List
from typing import Set
from typing import Tuple

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import replace_call

SIX_NATIVE_STR = frozenset(('ensure_str', 'ensure_text', 'text_type'))


def _fix_native_str(i: int, tokens: List[Token]) -> None:
    j = find_open_paren(tokens, i)
    func_args, end = parse_call_args(tokens, j)
    if any(tok.name == 'NL' for tok in tokens[i:end]):
        return
    if func_args:
        replace_call(tokens, i, end, func_args, '{args[0]}')
    else:
        tokens[i:end] = [tokens[i]._replace(name='STRING', src="''")]


def is_a_native_literal_call(
        node: ast.Call,
        from_imports: Dict[str, Set[str]],
) -> bool:
    return (
        (
            is_name_attr(node.func, from_imports, 'six', SIX_NATIVE_STR) or
            isinstance(node.func, ast.Name) and node.func.id == 'str'
        ) and
        not node.keywords and
        not has_starargs(node) and
        (
            len(node.args) == 0 or
            (len(node.args) == 1 and isinstance(node.args[0], ast.Str))
        )
    )


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            is_a_native_literal_call(node, state.from_imports)
    ):
        yield ast_to_offset(node), _fix_native_str
