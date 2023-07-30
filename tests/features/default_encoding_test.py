from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('"asd".encode("utf-8")', '"asd".encode()'),
        ('f"asd".encode("utf-8")', 'f"asd".encode()'),
        ('f"{3}asd".encode("utf-8")', 'f"{3}asd".encode()'),
        ('fr"asd".encode("utf-8")', 'fr"asd".encode()'),
        ('r"asd".encode("utf-8")', 'r"asd".encode()'),
        ('"asd".encode("utf8")', '"asd".encode()'),
        ('"asd".encode("UTF-8")', '"asd".encode()'),
        pytest.param(
            '"asd".encode(("UTF-8"))',
            '"asd".encode()',
            id='parenthesized encoding',
        ),
        (
            'sys.stdout.buffer.write(\n    "a"\n    "b".encode("utf-8")\n)',
            'sys.stdout.buffer.write(\n    "a"\n    "b".encode()\n)',
        ),
        (
            'x = (\n'
            '    "y\\u2603"\n'
            ').encode("utf-8")\n',
            'x = (\n'
            '    "y\\u2603"\n'
            ').encode()\n',
        ),
        pytest.param(
            'f"{x}(".encode("utf-8")',
            'f"{x}(".encode()',
            id='3.12+ handle open brace in fstring',
        ),
    ),
)
def test_fix_encode(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected


@pytest.mark.parametrize(
    's',
    (
        # non-utf-8 codecs should not be changed
        '"asd".encode("unknown-codec")',
        '"asd".encode("ascii")',

        # only autofix string literals to avoid false positives
        'x="asd"\nx.encode("utf-8")',

        # the current version is too timid to handle these
        '"asd".encode("utf-8", "strict")',
        '"asd".encode(encoding="utf-8")',
    ),
)
def test_fix_encode_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s
