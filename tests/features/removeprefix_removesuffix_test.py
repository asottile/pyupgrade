from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_noop_before_39():
    s = '''\
if x.startswith(S):
    x = x[len(S):]
elif x.endswith(T):
    x = x[:-1 * len(T)]
'''
    assert _fix_plugins(s, settings=Settings(min_version=(3, 8))) == s


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'if s.startswith("a"):\n'
            '    s = s.lstrip("a")\n',
            id='unrelated',
        ),
        pytest.param(
            'if s.startswith(x):\n'
            '    s = s[2:]\n',
            id='cannot prove x is 2',
        ),
        pytest.param(
            'if s.startswith(x):\n'
            '    s = s[len(x):]\n'
            'else:\n'
            '    print("no!)")\n',
            id='has else',
        ),
        pytest.param(
            'if something:\n'
            '    print("something!")\n'
            'elif s.startswith(x):\n'
            '    s = s[len(x):]\n',
            id='has elif',
        ),
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 9))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'if s.startswith("foo"):\n'
            '    s = s[len("foo"):]\n',

            's = s.removeprefix("foo")\n',

            id='removeprefix literal',
        ),
        pytest.param(
            'if s.startswith(S):\n'
            '    s = s[len(S):]\n',

            's = s.removeprefix(S)\n',

            id='removeprefix constant',
        ),
        pytest.param(
            'if s.endswith("foo"):\n'
            '    s = s[:-1 * len("foo")]\n',

            's = s.removesuffix("foo")\n',

            id='removesuffix literal',
        ),
        pytest.param(
            'if s.endswith(S):\n'
            '    s = s[:-1 * len(S)]\n',

            's = s.removesuffix(S)\n',

            id='removesuffix constant',
        ),
        pytest.param(
            'if s.startswith(x):\n'
            '    s = s[len(x):]  # TODO: removeprefix\n'
            '# after\n',

            's = s.removeprefix(x)\n'
            '# after\n',

            id='with comment',
        ),
        pytest.param(
            'if True:\n'
            '    if s.startswith(x):\n'
            '        s = s[len(x):]\n',

            'if True:\n'
            '    s = s.removeprefix(x)\n',

            id='allowed inside if',
        ),
        pytest.param(
            'if True:\n'
            '    something_else()\n'
            '    if s.startswith(x):\n'
            '        s = s[len(x):]\n'
            '    another_thing()\n',

            'if True:\n'
            '    something_else()\n'
            '    s = s.removeprefix(x)\n'
            '    another_thing()\n',

            id='inside block with other statements',
        ),
        pytest.param(
            'if (\n'
            '    x.startswith(y)\n'
            '):\n'
            '    x = x[len(y):]\n',

            'x = x.removeprefix(y)\n',

            id='if with parens',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 9)))
    assert ret == expected
