from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # non-ascii bytestring
        'print(six.b("£"))',
        # extra whitespace
        'print(six.b(   "123"))',
        # cannot determine args to rewrite them
        'six.b(*a)',
    ),
)
def test_six_b_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'six.b("123")',
            'b"123"',
        ),
        (
            'six.b(r"123")',
            'br"123"',
        ),
        (
            r'six.b("\x12\xef")',
            r'b"\x12\xef"',
        ),
        (
            'six.ensure_binary("foo")',
            'b"foo"',
        ),
        (
            'from six import b\n\n' r'b("\x12\xef")',
            'from six import b\n\n' r'b"\x12\xef"',
        ),
    ),
)
def test_six_b(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
