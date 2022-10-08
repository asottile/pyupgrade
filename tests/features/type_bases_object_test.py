from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('src', 'expected'),
    (
        ('A = type("A", (), {})', 'A = type("A", (), {})'),
        ('B = type("B", (int,), {}', 'B = type("B", (int,), {}'),
    ),
)
def test_fix_type_bases_object_noop(src, expected):
    ret = _fix_plugins(src, settings=Settings())
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('A = type("A", (object,), {})', 'A = type("A", (), {})'),
        ('B = type("B", (object, tuple), {})', 'B = type("B", (tuple,), {})'),
        (
            'C = type("C", (object, foo, bar), {})',
            'C = type("C", (foo, bar), {})',
        ),
        ('D = type("D", (tuple, object), {})', 'D = type("D", (tuple,), {})'),
        (
            'E = type("E", (foo, bar, object), {})',
            'E = type("E", (foo, bar), {})',
        ),
    ),
)
def test_fix_type_bases_object(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
