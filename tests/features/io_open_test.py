from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_fix_io_open_noop():
    src = '''\
from io import open
with open("f.txt") as f:
    print(f.read())
'''
    expected = '''\
with open("f.txt") as f:
    print(f.read())
'''
    ret = _fix_plugins(src, settings=Settings())
    assert ret == expected


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
    ),
)
def test_fix_io_open(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
