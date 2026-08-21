from __future__ import annotations

import ast
from collections.abc import Iterable

from tokenize_rt import Offset

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import remove_decorator
from pyupgrade._version_expr import always_false
from pyupgrade._version_expr import norm_min_version


def _visit_func_or_class(
        state: State,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    min_version = norm_min_version(state.settings.min_version)

    for decorator in node.decorator_list:
        if (
                isinstance(decorator, ast.Call) and
                isinstance(decorator.func, ast.Attribute) and
                decorator.func.attr == 'skipif' and
                is_name_attr(
                    decorator.func.value,
                    state.from_imports,
                    ('pytest',),
                    ('mark',),
                ) and
                not has_starargs(decorator) and
                len(decorator.args) == 1 and
                always_false(decorator.args[0], state, min_version)
        ):
            yield ast_to_offset(decorator), remove_decorator
        # TODO: could also do `always_true` and remove the whole test / class


register(ast.ClassDef)(_visit_func_or_class)
register(ast.FunctionDef)(_visit_func_or_class)
register(ast.AsyncFunctionDef)(_visit_func_or_class)
