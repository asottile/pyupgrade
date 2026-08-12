from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_noop_before_315():
    s = 'open("foo", encoding="utf-8")'
    assert _fix_plugins(s, settings=Settings(min_version=(3, 14))) == s


@pytest.mark.parametrize(
    's',
    (
        # already removed
        'open("foo")',
        # alternative encoding
        'open("foo", encoding="latin1")',
        'open("foo", encoding="us-ascii")',
        # don't remove this, they meant to use `encoding=`
        'open("foo", "r", "utf-8")',
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 15))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'open("foo", encoding="utf-8")\n',
            'open("foo")\n',
            id='simple case',
        ),
        pytest.param(
            'open("foo", encoding="UTF8")\n',
            'open("foo")\n',
            id='alternative spelling',
        ),
        pytest.param(
            'open(*args, encoding="utf-8")',
            'open(*args)',
            id='starargs',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert ret == expected
