from __future__ import annotations

import ast
import functools
from typing import Iterable

from tokenize_rt import Offset

from .collections_import_of_abcs import _ABC_NAMES
from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import replace_name


@register(ast.Attribute)
def visit_Attribute(
        state: State,
        node: ast.Attribute,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            # state.settings.min_version >= (3,) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'collections' and
            node.attr in _ABC_NAMES
    ):
        func = functools.partial(
            replace_name,
            name=node.value.id,
            new='collections.abc',
        )
        yield ast_to_offset(node), func
