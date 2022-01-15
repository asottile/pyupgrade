from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'type("")\n',
            (2, 7),
            id='not python 3+',
        ),
        pytest.param(
            'type(None)\n',
            (3,),
            id='NoneType',
        ),
        pytest.param(
            'foo = "foo"\n'
            'type(foo)\n',
            (3,),
            id='String assigned to variable',
        ),
    ),
)
def test_fix_type_of_primitive_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


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
    ),
)
def test_fix_type_of_primitive(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3,)))
    assert ret == expected
