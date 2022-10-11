from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    'src',
    ['A = type("A", (), {})', 'B = type("B", (int,), {}'],
)
def test_fix_type_bases_object_noop(src):
    ret = _fix_plugins(src, settings=Settings())
    assert ret == src


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'A = type("A", (object,), {})',
            'A = type("A", (), {})',
            id='only object base class',
        ),
        pytest.param(
            'B = type("B", (object, tuple), {})',
            'B = type("B", (tuple,), {})',
            id='two base classes, object first',
        ),
        pytest.param(
            'C = type("C", (object, foo, bar), {})',
            'C = type("C", (foo, bar), {})',
            id='three base classes, object first',
        ),
        pytest.param(
            'D = type("D", (tuple, object), {})',
            'D = type("D", (tuple,), {})',
            id='two base classes, object last',
        ),
        pytest.param(
            'E = type("E", (foo, bar, object), {})',
            'E = type("E", (foo, bar), {})',
            id='three base classes, object last',
        ),
    ),
)
def test_fix_type_bases_object(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
