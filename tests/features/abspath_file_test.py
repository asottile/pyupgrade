from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from os.path import abspath\n'
            'abspath(__file__)',
            'from os.path import abspath\n'
            '__file__',
            id='abspath',
        ),
        pytest.param(
            'import os\n'
            'os.path.abspath(__file__)',
            'import os\n'
            '__file__',
            id='os.path.abspath',
        ),
    ),
)
def test_fix_abspath_file(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 9)))
    assert ret == expected


@pytest.mark.parametrize(
    's, min_version',
    (
        pytest.param(
            'abspath(__file__)',
            (3, 8),
            id='Not Python3.9+',
        ),
        pytest.param(
            'os.path.abspath(file)',
            (3, 9),
            id='Abspath of not-__file__',
        ),
        pytest.param(
            'os.path.abspath(file, foo)',
            (3, 9),
            id='Garbage (don\'t rewrite)',
        ),
    ),
)
def test_fix_abspath_file_noop(s, min_version):
    assert _fix_plugins(s, settings=Settings(min_version=min_version)) == s
