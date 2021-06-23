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
from pyupgrade._token_helpers import find_token


def _replace_celementtree_with_elementtree(
        i: int,
        tokens: List[Token],
) -> None:
    j = find_token(tokens, i, 'cElementTree')
    tokens[j] = tokens[j]._replace(src='ElementTree')


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            node.module == 'xml.etree.cElementTree' and
            node.level == 0
    ):
        yield ast_to_offset(node), _replace_celementtree_with_elementtree


@register(ast.Import)
def visit_Import(
        state: State,
        node: ast.Import,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if (
        state.settings.min_version >= (3,) and
        len(node.names) == 1 and
        node.names[0].name == 'xml.etree.cElementTree' and
        node.names[0].asname is not None
    ):
        yield ast_to_offset(node), _replace_celementtree_with_elementtree
