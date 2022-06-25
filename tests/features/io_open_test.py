from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # when using open without referencing io we don't need to rewrite
        'from io import open\n\n'
        'with open("f.txt") as f:\n'
        '     print(f.read())\n',
    ),
)
def test_fix_io_open_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'import io\n\n'
            'with io.open("f.txt", mode="r", buffering=-1, **kwargs) as f:\n'
            '   print(f.read())\n',

            'import io\n\n'
            'with open("f.txt", mode="r", buffering=-1, **kwargs) as f:\n'
            '   print(f.read())\n',
        ),
        (
            'import io\n\n'
            'with io.open("f.txt", "r") as f:\n'
            '   print(f.read())\n',

            'import io\n\n'
            'with open("f.txt") as f:\n'
            '   print(f.read())\n',
        ),
        ('io.open("foo", "U")', 'open("foo")'),
        ('io.open("foo", mode="U")', 'open("foo")'),
        ('io.open("foo", "Ur")', 'open("foo")'),
        ('io.open("foo", mode="Ur")', 'open("foo")'),
        ('io.open("foo", "Ub")', 'open("foo", "rb")'),
        ('io.open("foo", mode="Ub")', 'open("foo", mode="rb")'),
        ('io.open("foo", "rUb")', 'open("foo", "rb")'),
        ('io.open("foo", mode="rUb")', 'open("foo", mode="rb")'),
        ('io.open("foo", "r")', 'open("foo")'),
        ('io.open("foo", mode="r")', 'open("foo")'),
        ('io.open("foo", "rt")', 'open("foo")'),
        ('io.open("foo", mode="rt")', 'open("foo")'),
        ('io.open("f", "r", encoding="UTF-8")', 'open("f", encoding="UTF-8")'),
        (
            'io.open("f", mode="r", encoding="UTF-8")',
            'open("f", encoding="UTF-8")',
        ),
        (
            'io.open(file="f", mode="r", encoding="UTF-8")',
            'open(file="f", encoding="UTF-8")',
        ),
        (
            'io.open("f", encoding="UTF-8", mode="r")',
            'open("f", encoding="UTF-8")',
        ),
        (
            'io.open(file="f", encoding="UTF-8", mode="r")',
            'open(file="f", encoding="UTF-8")',
        ),
        (
            'io.open(mode="r", encoding="UTF-8", file="t.py")',
            'open(encoding="UTF-8", file="t.py")',
        ),
    ),
)
def test_fix_io_open(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3,)))
    assert ret == expected
