from __future__ import annotations

import ast

from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import State
from pyupgrade._data import Version


def norm_min_version(version: Version) -> tuple[int, int]:
    if version == (3,):
        return (3, 0)
    else:
        assert len(version) == 2, version
        return version


def _cmp(test: ast.Compare, op: type[ast.cmpop], n: int) -> bool:
    return (
        isinstance(test.ops[0], op) and
        isinstance(test.comparators[0], ast.Constant) and
        test.comparators[0].value == n
    )


def _eq(test: ast.Compare, n: int) -> bool:
    return _cmp(test, ast.Eq, n)


def _lt(test: ast.Compare, n: int) -> bool:
    return _cmp(test, ast.Lt, n)


def _gte(test: ast.Compare, n: int) -> bool:
    return _cmp(test, ast.GtE, n)


def _compare_to_3(
        test: ast.Compare,
        op: type[ast.cmpop] | tuple[type[ast.cmpop], ...],
        minor: int = 0,
) -> bool:
    if not (
            isinstance(test.ops[0], op) and
            isinstance(test.comparators[0], ast.Tuple) and
            len(test.comparators[0].elts) >= 1
    ):
        return False

    elts_l = []
    for n in test.comparators[0].elts:
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            elts_l.append(n.value)
        else:
            return False

    # padding a 0 for compatibility with (3,) used as a spec
    elts = (*elts_l, 0)

    return elts[:2] == (3, minor) and all(n == 0 for n in elts[2:])


def always_false(
        test: ast.expr,
        state: State,
        min_version: tuple[int, int],
) -> bool:
    return (
        # if six.PY2:
        is_name_attr(test, state.from_imports, ('six',), ('PY2',)) or
        # if not six.PY3:
        (
            isinstance(test, ast.UnaryOp) and
            isinstance(test.op, ast.Not) and
            is_name_attr(test.operand, state.from_imports, ('six',), ('PY3',))
        ) or
        # sys.version_info == 2 or < (3,)
        # or < (3, n) or <= (3, n) (with n<m)
        (
            isinstance(test, ast.Compare) and
            is_name_attr(
                test.left,
                state.from_imports,
                ('sys',),
                ('version_info',),
            ) and
            len(test.ops) == 1 and (
                _eq(test, 2) or
                _compare_to_3(test, ast.Lt, min_version[1]) or
                any(
                    _compare_to_3(test, (ast.Lt, ast.LtE), minor)
                    for minor in range(min_version[1])
                )
            )
        ) or
        # sys.version_info[0] == 2 or < 3
        # sys.version_info.major == 2 or < 3
        (
            isinstance(test, ast.Compare) and
            (
                (
                    isinstance(test.left, ast.Subscript) and
                    isinstance(test.left.slice, ast.Constant) and
                    test.left.slice.value == 0
                ) or
                (
                    isinstance(test.left, ast.Attribute) and
                    test.left.attr == 'major'
                )
            ) and
            is_name_attr(
                test.left.value,
                state.from_imports,
                ('sys',),
                ('version_info',),
            ) and
            len(test.ops) == 1 and
            (
                _eq(test, 2) or
                _lt(test, 3)
            )
        ) or (
            isinstance(test, ast.BoolOp) and
            isinstance(test.op, ast.And) and
            any(always_false(val, state, min_version) for val in test.values)
        )
    )


def always_true(
        test: ast.expr,
        state: State,
        min_version: tuple[int, int],
) -> bool:
    return (
        # if six.PY3:
        is_name_attr(test, state.from_imports, ('six',), ('PY3',)) or
        # if not six.PY2:
        (
            isinstance(test, ast.UnaryOp) and
            isinstance(test.op, ast.Not) and
            is_name_attr(test.operand, state.from_imports, ('six',), ('PY2',))
        ) or
        # sys.version_info == 3 or >= (3,) or > (3,)
        # sys.version_info >= (3, n) (with n<=m)
        # or sys.version_info > (3, n) (with n<m)
        (
            isinstance(test, ast.Compare) and
            is_name_attr(
                test.left,
                state.from_imports,
                ('sys',),
                ('version_info',),
            ) and
            len(test.ops) == 1 and (
                _eq(test, 3) or
                _compare_to_3(test, (ast.Gt, ast.GtE)) or
                _compare_to_3(test, ast.GtE, min_version[1]) or
                any(
                    _compare_to_3(test, (ast.Gt, ast.GtE), minor)
                    for minor in range(min_version[1])
                )
            )
        ) or
        # sys.version_info[0] == 3 or >= 3
        # sys.version_info.major == 3 or >= 3
        (
            isinstance(test, ast.Compare) and
            (
                (
                    isinstance(test.left, ast.Subscript) and
                    isinstance(test.left.slice, ast.Constant) and
                    test.left.slice.value == 0
                ) or
                (
                    isinstance(test.left, ast.Attribute) and
                    test.left.attr == 'major'
                )
            ) and
            is_name_attr(
                test.left.value,
                state.from_imports,
                ('sys',),
                ('version_info',),
            ) and
            len(test.ops) == 1 and
            (
                _eq(test, 3) or
                _gte(test, 3)
            )
        ) or (
            isinstance(test, ast.BoolOp) and
            isinstance(test.op, ast.Or) and
            any(always_true(val, state, min_version) for val in test.values)
        )
    )
