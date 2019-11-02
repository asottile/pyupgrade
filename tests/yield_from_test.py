# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import ast
import sys

import pytest

from pyupgrade import _fix_py3_plus
from pyupgrade import fields_same
from pyupgrade import targets_same


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'def f():\n'
            '    for x in y:\n'
            '        yield x',
            'def f():\n'
            '    yield from y\n',
        ),
        (
            'def f():\n'
            '    for x in [1, 2, 3]:\n'
            '        yield x',
            'def f():\n'
            '    yield from [1, 2, 3]\n',
        ),
        (
            'def f():\n'
            '    for x in {x for x in y}:\n'
            '        yield x',
            'def f():\n'
            '    yield from {x for x in y}\n',
        ),
        (
            'def f():\n'
            '    for x in (1, 2, 3):\n'
            '        yield x',
            'def f():\n'
            '    yield from (1, 2, 3)\n',
        ),
        (
            'def f():\n'
            '    for x, y in {3: "x", 6: "y"}:\n'
            '        yield x, y',
            'def f():\n'
            '    yield from {3: "x", 6: "y"}\n',
        ),
        (
            'def f():  # Comment one\n'
            '    # Comment two\n'
            '    for x, y in {  # Comment three\n'
            '       3: "x",  # Comment four\n'
            '       # Comment five\n'
            '       6: "y"  # Comment six\n'
            '    }:  # Comment seven\n'
            '       # Comment eight\n'
            '       yield x, y  # Comment nine\n'
            '       # Comment ten',
            'def f():  # Comment one\n'
            '    # Comment two\n'
            '    yield from {  # Comment three\n'
            '       3: "x",  # Comment four\n'
            '       # Comment five\n'
            '       6: "y"  # Comment six\n'
            '    }\n',
        ),
        (
            'def f():\n'
            '    for x, y in [{3: (3, [44, "long ss"]), 6: "y"}]:\n'
            '        yield x, y',
            'def f():\n'
            '    yield from [{3: (3, [44, "long ss"]), 6: "y"}]\n',
        ),
        (
            'def f():\n'
            '    for x, y in z():\n'
            '        yield x, y',
            'def f():\n'
            '    yield from z()\n',
        ),
        (
            'def f():\n'
            '    def func():\n'
            '        # This comment is preserved\n'
            '\n'
            '        for x, y in z():  # Comment one\n'
            '\n'
            '            # Commment two\n'
            '            yield x, y  # Comment three\n'
            '            # Comment four\n'
            '\n\n'
            '# Comment\n'
            'def g():\n'
            '    print(3)',
            'def f():\n'
            '    def func():\n'
            '        # This comment is preserved\n'
            '\n'
            '        yield from z()\n'
            '\n\n'
            '# Comment\n'
            'def g():\n'
            '    print(3)',
        ),
        pytest.param(
            'def f():\n'
            '    x = None\n'
            '    for x in z:\n'
            '        yield x\n',
            'def f():\n'
            '    x = None\n'
            '    yield from z\n',
            id='loop variable assigned before the loop',
        ),
        pytest.param(
            'def f():\n'
            '    for x in z:\n'
            '        yield x\n'
            '    x = None\n',
            'def f():\n'
            '    yield from z\n'
            '    x = None\n',
            id='loop variable assigned after the loop',
        ),
        pytest.param(
            'def f():\n'
            '    print(x)\n'
            '    for x in z:\n'
            '        yield x\n',
            'def f():\n'
            '    print(x)\n'
            '    yield from z\n',
            id='loop variable referenced before the loop',
        ),
        pytest.param(
            'def f():\n'
            '    print(w)\n'
            '    for x in z:\n'
            '        yield x\n',
            'def f():\n'
            '    print(w)\n'
            '    yield from z\n',
            id='non-loop variable referenced before the loop',
        ),
        pytest.param(
            'def f():\n'
            '    for x in z:\n'
            '        yield x\n'
            '    print(w)\n',
            'def f():\n'
            '    yield from z\n'
            '    print(w)\n',
            id='non-loop variable referenced after the loop',
        ),
        pytest.param(
            'def f():\n'
            '    for x in z:\n'
            '        yield x\n'
            '    for y in w:\n'
            '        print(y)\n',
            'def f():\n'
            '    yield from z\n'
            '    for y in w:\n'
            '        print(y)\n',
            id='multiple for loops',
        ),
    ),
)
def test_fix_yield_from(s, expected):
    assert _fix_py3_plus(s) == expected


@pytest.mark.xfail(
    sys.version_info < (3, 5),
    reason='async introduced in python 3.5',
)
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'async def f():\n'
            '    for x in [1, 2]:\n'
            '        yield x\n'
            '\n'
            '    def g():\n'
            '        for x in [1, 2, 3]:\n'
            '            yield x\n'
            '\n'
            '    for x in [1, 2]:\n'
            '        yield x\n'
            '\n'
            '    return g',
            'async def f():\n'
            '    for x in [1, 2]:\n'
            '        yield x\n'
            '\n'
            '    def g():\n'
            '        yield from [1, 2, 3]\n'
            '\n'
            '    for x in [1, 2]:\n'
            '        yield x\n'
            '\n'
            '    return g',
        ),
    ),
)
def test_fix_async_yield_from(s, expected):
    assert _fix_py3_plus(s) == expected


@pytest.mark.parametrize(
    's',
    (
        'def f():\n'
        '    for x in z:\n'
        '        yield',
        'def f():\n'
        '    for x in z:\n'
        '        yield y',
        'def f():\n'
        '    for x, y in z:\n'
        '        yield x',
        'def f():\n'
        '    for x, y in z:\n'
        '        yield y',
        'def f():\n'
        '    for a, b in z:\n'
        '        yield x, y',
        'def f():\n'
        '    for x, y in z:\n'
        '        yield y, x',
        'def f():\n'
        '    for x, y, c in z:\n'
        '        yield x, y',
        'def f():\n'
        '    for x in z:\n'
        '        x = 22\n'
        '        yield x',
        'def f():\n'
        '    for x in z:\n'
        '        yield x\n'
        '    else:\n'
        '        print("boom!")\n',
        pytest.param(
            'for x in z:\n'
            '    yield x\n',
            id='yield outside function',
        ),
        pytest.param(
            'def f():\n'
            '    x = None\n'
            '    for x in z:\n'
            '        yield x\n'
            '    print(x)\n',
            id='loop variable referenced after the loop',
        ),
        pytest.param(
            'def f():\n'
            '    def b():\n'
            '        x = None\n'
            '        for x in z:\n'
            '            yield x\n'
            '         print(x)\n',
            id='loop variable referenced after the loop, nested funcs',
        ),
        pytest.param(
            'def f():\n'
            '    x = None\n'
            '    for x, y in z:\n'
            '        yield x, y\n'
            '    print(x)\n',
            id='multiple loop variables referenced after the loop',
        ),
    ),
)
def test_fix_yield_from_noop(s):
    assert _fix_py3_plus(s) == s


def test_targets_same():
    assert targets_same(ast.parse('global a, b'), ast.parse('global a, b'))
    assert not targets_same(ast.parse('global a'), ast.parse('global b'))


def _get_body(expr):
    body = ast.parse(expr).body[0]
    assert isinstance(body, ast.Expr)
    return body.value


def test_fields_same():
    assert not fields_same(_get_body('x'), _get_body('1'))
