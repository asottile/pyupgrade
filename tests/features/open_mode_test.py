from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # already a reduced mode
        'open("foo", "w")',
        'open("foo", mode="w")',
        'open("foo", "rb")',
        'open("foo", "r")',
        'open("f", "r", encoding="UTF-8")',
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
        ('open("foo", "Ur")', 'open("foo", "r")'),
        ('open("foo", mode="Ur")', 'open("foo", mode="r")'),
        ('open("foo", "Ub")', 'open("foo", "rb")'),
        ('open("foo", mode="Ub")', 'open("foo", mode="rb")'),
        ('open("foo", "rUb")', 'open("foo", "rb")'),
        ('open("foo", mode="rUb")', 'open("foo", mode="rb")'),
        ('open("foo", "wt")', 'open("foo", "w")'),
        ('open("foo", mode="wt")', 'open("foo", mode="w")'),
        ('open("foo", "rt")', 'open("foo", "r")'),
        ('open("foo", mode="rt")', 'open("foo", mode="r")'),
        (
            'open("f", "wt", encoding="UTF-8")',
            'open("f", "w", encoding="UTF-8")',
        ),
        (
            'open("f", mode="tw", encoding="UTF-8")',
            'open("f", mode="w", encoding="UTF-8")',
        ),
        (
            'open(file="f", mode="wt", encoding="UTF-8")',
            'open(file="f", mode="w", encoding="UTF-8")',
        ),
        (
            'open("f", encoding="UTF-8", mode="wt")',
            'open("f", encoding="UTF-8", mode="w")',
        ),
        (
            'open(file="f", encoding="UTF-8", mode="wt")',
            'open(file="f", encoding="UTF-8", mode="w")',
        ),
        (
            'open(mode="wt", encoding="UTF-8", file="t.py")',
            'open(mode="w", encoding="UTF-8", file="t.py")',
        ),
        pytest.param('open(f, u"U")', 'open(f)', id='string with u flag'),
        pytest.param(
            'io.open("foo", "U")',
            'open("foo")',
            id='io.open also rewrites modes in a single pass',
        ),
    ),
)
def test_fix_open_mode(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
