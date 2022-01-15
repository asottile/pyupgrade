from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'sum((i for i in range(3)))',
            id='Parenthesised generator expression',
        ),
        pytest.param(
            'len([i for i in range(2)])',
            id='Non-supported function',
        ),
        pytest.param('frozenset()', id='no arguments'),
        pytest.param(
            '"".join([[i for _ in range(2)] for i in range(3)])\n',
            id='string join (left alone for perf reasons)',
        ),
        pytest.param(
            'async def foo():\n'
            '    for i in range(3):\n'
            '        yield i\n'
            'async def bar():\n'
            '    sum([i async for i in foo()])\n',
            id='Contains async',
        ),
        pytest.param(
            'tuple([\n'
            '    await self._configure_component(hass, controller_config)\n'
            '    for controller_config in configs\n'
            '])\n',
            id='Contains await',
        ),
    ),
)
def test_fix_generator_expressions_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'sum([i for i in range(3)])\n',

            'sum(i for i in range(3))\n',

            id='Single line, list comprehension\n',
        ),
        pytest.param(
            'sum([i for i in range(2)], 2)',

            'sum((i for i in range(2)), 2)',

            id='List comprehension plus posarg',
        ),
        pytest.param(
            'sum([i for i in range(2)], x=2)',

            'sum((i for i in range(2)), x=2)',

            id='List comprehension plus kwarg',
        ),
        pytest.param(
            'sum(([i for i in range(3)]))\n',

            'sum((i for i in range(3)))\n',

            id='Parenthesised list comprehension\n',
        ),
        pytest.param(
            'sum(\n'
            '    [i for i in range(3)]\n'
            ')\n',

            'sum(\n'
            '    i for i in range(3)\n'
            ')\n',

            id='Multiline list comprehension\n',
        ),
        pytest.param(
            'sum([[i for _ in range(2)] for i in range(3)])\n',

            'sum([i for _ in range(2)] for i in range(3))\n',

            id='Nested list comprehension\n',
        ),
        pytest.param(
            'sum([[i for _ in range(2)] for i in range(3)],)\n',

            'sum([i for _ in range(2)] for i in range(3))\n',

            id='Trailing comma after list comprehension',
        ),
        pytest.param(
            'sum(\n'
            '    [\n'
            '        i for i in range(3)\n'
            '    ],\n'
            ')\n',

            'sum(\n'
            '    \n'
            '        i for i in range(3)\n'
            '    \n'
            ')\n',

            id='Multiline list comprehension with trailing comma\n',
        ),
    ),
)
def test_fix_generator_expressions(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
