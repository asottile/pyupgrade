from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('src', 'expected'),
    (
        ('A = type("A", (), {})', 'A = type("A", (), {})'),
        ('type("C", (int,), {}', 'type("C", (int,), {}'),
    ),
)
def test_fix_type_bases_object_noop(src, expected):
    ret = _fix_plugins(src, settings=Settings())
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('type("A", (object,), {})', 'type("A", (), {})'),
        ('type("B", (object, tuple), {})', 'type("B", (tuple,), {})'),
        ('type("B", (object, foo, bar), {})', 'type("B", (foo, bar), {})'),
        ('type("B", (tuple, object), {})', 'type("B", (tuple,), {})'),
        ('type("B", (foo, bar, object), {})', 'type("B", (foo, bar), {})'),
    ),
)
def test_fix_type_bases_object(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
