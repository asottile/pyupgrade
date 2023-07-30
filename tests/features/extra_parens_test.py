from __future__ import annotations

import pytest

from pyupgrade._main import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        'print("hello world")',
        'print((1, 2, 3))',
        'print(())',
        'print((\n))',
        # don't touch parenthesized generators
        'sum((block.code for block in blocks), [])',
        # don't touch coroutine yields
        'def f():\n'
        '    x = int((yield 1))\n',
    ),
)
def test_fix_extra_parens_noop(s):
    assert _fix_tokens(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('print(("hello world"))', 'print("hello world")'),
        ('print(("foo{}".format(1)))', 'print("foo{}".format(1))'),
        ('print((((1))))', 'print(1)'),
        (
            'print(\n'
            '    ("foo{}".format(1))\n'
            ')',

            'print(\n'
            '    "foo{}".format(1)\n'
            ')',
        ),
        (
            'print(\n'
            '    (\n'
            '        "foo"\n'
            '    )\n'
            ')\n',

            'print(\n'
            '        "foo"\n'
            ')\n',
        ),
        pytest.param(
            'def f():\n'
            '    x = int(((yield 1)))\n',

            'def f():\n'
            '    x = int((yield 1))\n',

            id='extra parens on coroutines are instead reduced to 2',
        ),
        pytest.param(
            'f((f"{x})"))',
            'f(f"{x})")',
            id='3.12: handle close brace in fstring body',
        ),
        pytest.param(
            'f((f"{x}("))',
            'f(f"{x}(")',
            id='3.12: handle open brace in fstring body',
        ),
    ),
)
def test_fix_extra_parens(s, expected):
    assert _fix_tokens(s) == expected
