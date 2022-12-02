from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'import datetime\n'
            'print(datetime.timezone(-1))',

            id='not rewriting timezone object to alias',
        ),
    ),
)
def test_fix_datetime_utc_alias_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == s
    assert _fix_plugins(s, settings=Settings(min_version=(3, 11))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import datetime\n'
            'print(datetime.timezone.utc)',

            'import datetime\n'
            'print(datetime.UTC)',

            id='rewriting to alias',
        ),
    ),
)
def test_fix_datetime_utc_alias(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == s
    assert _fix_plugins(s, settings=Settings(min_version=(3, 11))) == expected
