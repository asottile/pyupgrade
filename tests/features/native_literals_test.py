from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        'str(1)',
        'str("foo"\n"bar")',  # creates a syntax error
        'str(*a)', 'str("foo", *a)',
        'str(**k)', 'str("foo", **k)',
        'str("foo", encoding="UTF-8")',
        'bytes("foo", encoding="UTF-8")',
        'bytes(b"foo"\nb"bar")',
        'bytes("foo"\n"bar")',
        'bytes(*a)', 'bytes("foo", *a)',
        'bytes("foo", **a)',
    ),
)
def test_fix_native_literals_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('str()', "''"),
        ('str("foo")', '"foo"'),
        ('str("""\nfoo""")', '"""\nfoo"""'),
        ('six.ensure_str("foo")', '"foo"'),
        ('six.ensure_text("foo")', '"foo"'),
        ('six.text_type("foo")', '"foo"'),
        pytest.param(
            'from six import text_type\n'
            'text_type("foo")\n',

            'from six import text_type\n'
            '"foo"\n',

            id='from import of rewritten name',
        ),
        ('bytes()', "b''"),
        ('bytes(b"foo")', 'b"foo"'),
        ('bytes(b"""\nfoo""")', 'b"""\nfoo"""'),
    ),
)
def test_fix_native_literals(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
