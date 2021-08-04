import ast
from typing import Iterable
from typing import Tuple

from tokenize_rt import Offset

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_async_listcomp
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import replace_list_comp_brackets


@register(ast.Starred)
def visit_Starred(
        state: State,
        node: ast.Starred,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
        state.settings.min_version >= (3,) and
        isinstance(node.value, ast.ListComp) and
        not is_async_listcomp(node.value)
    ):
        yield ast_to_offset(node.value), replace_list_comp_brackets
