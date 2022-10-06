from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins
from pyupgrade._plugins.open_mode import _permute
from pyupgrade._plugins.open_mode import _plus


def test_plus():
    assert _plus(('a',)) == ('a', 'a+')
    assert _plus(('a', 'b')) == ('a', 'b', 'a+', 'b+')


def test_permute():
    assert _permute('ab') == ('ab', 'ba')
    assert _permute('abc') == ('abc', 'acb', 'bac', 'bca', 'cab', 'cba')


@pytest.mark.parametrize(
    's',
    (
        # already a reduced mode
        'open("foo", "w")',
        'open("foo", mode="w")',
        'open("foo", "rb")',
        # nonsense mode
        'open("foo", "Uw")',
        'open("foo", qux="r")',
        'open("foo", 3)',
        'open(mode="r")',
        # don't remove this, they meant to use `encoding=`
        'open("foo", "r", "utf-8")',
    ),
)
def test_fix_open_mode_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('open("foo", "U")', 'open("foo")'),
        ('open("foo", mode="U")', 'open("foo")'),
        ('open("foo", "Ur")', 'open("foo")'),
        ('open("foo", mode="Ur")', 'open("foo")'),
        ('open("foo", "Ub")', 'open("foo", "rb")'),
        ('open("foo", mode="Ub")', 'open("foo", mode="rb")'),
        ('open("foo", "rUb")', 'open("foo", "rb")'),
        ('open("foo", mode="rUb")', 'open("foo", mode="rb")'),
        ('open("foo", "r")', 'open("foo")'),
        ('open("foo", mode="r")', 'open("foo")'),
        ('open("foo", "rt")', 'open("foo")'),
        ('open("foo", mode="rt")', 'open("foo")'),
        ('open("f", "r", encoding="UTF-8")', 'open("f", encoding="UTF-8")'),
        (
            'open("f", mode="r", encoding="UTF-8")',
            'open("f", encoding="UTF-8")',
        ),
        (
            'open(file="f", mode="r", encoding="UTF-8")',
            'open(file="f", encoding="UTF-8")',
        ),
        (
            'open("f", encoding="UTF-8", mode="r")',
            'open("f", encoding="UTF-8")',
        ),
        (
            'open(file="f", encoding="UTF-8", mode="r")',
            'open(file="f", encoding="UTF-8")',
        ),
        (
            'open(mode="r", encoding="UTF-8", file="t.py")',
            'open(encoding="UTF-8", file="t.py")',
        ),
        pytest.param('open(f, u"r")', 'open(f)', id='string with u flag'),
        pytest.param(
            'io.open("foo", "r")',
            'open("foo")',
            id='io.open also rewrites modes in a single pass',
        ),
        ('open("foo", "wt")', 'open("foo", "w")'),
        ('open("foo", "xt")', 'open("foo", "x")'),
        ('open("foo", "at")', 'open("foo", "a")'),
        ('open("foo", "wt+")', 'open("foo", "w+")'),
        ('open("foo", "rt+")', 'open("foo", "r+")'),
    ),
)
def test_fix_open_mode(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
