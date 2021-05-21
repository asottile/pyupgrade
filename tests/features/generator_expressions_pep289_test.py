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
    ),
)
def test_fix_typing_text_noop(s):
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
            '"".join([[i for _ in range(2)] for i in range(3)])\n',

            '"".join([i for _ in range(2)] for i in range(3))\n',

            id='Join function',
        ),
    ),
)
def test_fix_typing_text(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
