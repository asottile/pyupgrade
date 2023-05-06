from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'type(None)\n',
            id='NoneType',
        ),
        pytest.param(
            'type(...)\n',
            id='ellipsis',
        ),
        pytest.param(
            'foo = "foo"\n'
            'type(foo)\n',
            id='String assigned to variable',
        ),
    ),
)
def test_fix_type_of_primitive_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'type("")\n',

            'str\n',

            id='Empty string -> str',
        ),
        pytest.param(
            'type(0)\n',

            'int\n',

            id='zero -> int',
        ),
        pytest.param(
            'type(0.)\n',

            'float\n',

            id='decimal zero -> float',
        ),
        pytest.param(
            'type(0j)\n',

            'complex\n',

            id='0j -> complex',
        ),
        pytest.param(
            'type(b"")\n',

            'bytes\n',

            id='Empty bytes string -> bytes',
        ),
        pytest.param(
            'type(True)\n',

            'bool\n',

            id='bool',
        ),
    ),
)
def test_fix_type_of_primitive(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
