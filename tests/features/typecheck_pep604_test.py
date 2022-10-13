from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins



@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'isinstance(1, (int, str, dict))',
            'isinstance(1, int | str | dict)',

            id='replace tuple to union',
        ),
        pytest.param(
            'isinstance(1, int)',
            'isinstance(1, int)',

            id='no replace of type name',
        ),
        pytest.param(
            'isinstance(1, (int,))',
            'isinstance(1, (int,))',

            id='no replace of tuple with one type name',
        ),
    ),
)
def test_fix_typecheck_pep604(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 10))) == expected

