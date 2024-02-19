from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'from shlex import quote\n'
            '" ".join(quote(arg) for arg in cmd)\n',
            (3, 8),
            id='quote from-imported',
        ),
        pytest.param(
            'import shlex\n'
            '" ".join(shlex.quote(arg) for arg in cmd)\n',
            (3, 7),
            id='3.8+ feature',
        ),
    ),
)
def test_shlex_join_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import shlex\n'
            '" ".join(shlex.quote(arg) for arg in cmd)\n',

            'import shlex\n'
            'shlex.join(cmd)\n',

            id='generator expression',
        ),
        pytest.param(
            'import shlex\n'
            '" ".join([shlex.quote(arg) for arg in cmd])\n',

            'import shlex\n'
            'shlex.join(cmd)\n',

            id='list comprehension',
        ),
        pytest.param(
            'import shlex\n'
            '" ".join([shlex.quote(arg) for arg in cmd],)\n',

            'import shlex\n'
            'shlex.join(cmd)\n',

            id='removes trailing comma',
        ),
        pytest.param(
            'import shlex\n'
            '" ".join([shlex.quote(arg) for arg in ["a", "b", "c"]],)\n',

            'import shlex\n'
            'shlex.join(["a", "b", "c"])\n',

            id='more complicated iterable',
        ),
    ),
)
def test_shlex_join_fixes(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 8))) == expected
