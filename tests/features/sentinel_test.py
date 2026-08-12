from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_noop_pre_3_15():
    s = '_MISSING = object()\n'
    ret = _fix_plugins(s, Settings(min_version=(3, 14)))
    assert ret == s


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'if True:\n'
            '    _MISSING = object()\n',
            id='not directly at module scope',
        ),
        pytest.param(
            '_MISSING = _MISSING2 = object()\n',
            id='multi-assign',
        ),
        pytest.param(
            '_MISSING = object(int)\n',
            id='probably some other object idk',
        ),
    ),
)
def test_noop(s):
    assert _fix_plugins(s, Settings(min_version=(3, 15))) == s


def test_fix():
    s = '_MISSING = object()\n'
    expected = "_MISSING = sentinel('_MISSING')\n"
    assert _fix_plugins(s, Settings(min_version=(3, 15))) == expected
