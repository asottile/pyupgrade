from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'try: ...\n'
            'except Exception:\n'
            '    raise',
            id='empty raise',
        ),
        pytest.param(
            'try: ...\n'
            'except: ...\n',
            id='empty try-except',
        ),
        pytest.param(
            'try: ...\n'
            'except AssertionError: ...\n',
            id='unrelated exception type as name',
        ),
        pytest.param(
            'try: ...\n'
            'except (AssertionError,): ...\n',
            id='unrelated exception type as tuple',
        ),
        pytest.param(
            'try: ...\n'
            'except OSError: ...\n',
            id='already rewritten name',
        ),
        pytest.param(
            'try: ...\n'
            'except (TypeError, OSError): ...\n',
            id='already rewritten tuple',
        ),
        pytest.param(
            'from .os import error\n'
            'raise error(1)\n',
            id='same name as rewrite but relative import',
        ),
        pytest.param(
            'from os import error\n'
            'def f():\n'
            '    error = 3\n'
            '    return error\n',
            id='not rewriting outside of raise or except',
        ),
        pytest.param(
            'from os import error as the_roof\n'
            'raise the_roof()\n',
            id='ignoring imports with aliases',
        ),
        # TODO: could probably rewrite these but leaving for now
        pytest.param(
            'import os\n'
            'try: ...\n'
            'except (os).error: ...\n',
            id='weird parens',
        ),
    ),
)
def test_fix_exceptions_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'raise socket.timeout()',
            (3, 9),
            id='raise socket.timeout is noop <3.10',
        ),
        pytest.param(
            'try: ...\n'
            'except socket.timeout: ...\n',
            (3, 9),
            id='except socket.timeout is noop <3.10',
        ),
        pytest.param(
            'raise asyncio.TimeoutError()',
            (3, 10),
            id='raise asyncio.TimeoutError() is noop <3.11',
        ),
        pytest.param(
            'try: ...\n'
            'except asyncio.TimeoutError: ...\n',
            (3, 10),
            id='except asyncio.TimeoutError() is noop <3.11',
        ),
    ),
)
def test_fix_exceptions_version_specific_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'raise mmap.error(1)\n',
            'raise OSError(1)\n',
            id='mmap.error',
        ),
        pytest.param(
            'raise os.error(1)\n',
            'raise OSError(1)\n',
            id='os.error',
        ),
        pytest.param(
            'raise select.error(1)\n',
            'raise OSError(1)\n',
            id='select.error',
        ),
        pytest.param(
            'raise socket.error(1)\n',
            'raise OSError(1)\n',
            id='socket.error',
        ),
        pytest.param(
            'raise IOError(1)\n',
            'raise OSError(1)\n',
            id='IOError',
        ),
        pytest.param(
            'raise EnvironmentError(1)\n',
            'raise OSError(1)\n',
            id='EnvironmentError',
        ),
        pytest.param(
            'raise WindowsError(1)\n',
            'raise OSError(1)\n',
            id='WindowsError',
        ),
        pytest.param(
            'raise os.error\n',
            'raise OSError\n',
            id='raise exception type without call',
        ),
        pytest.param(
            'from os import error\n'
            'raise error(1)\n',
            'from os import error\n'
            'raise OSError(1)\n',
            id='raise via from import',
        ),
        pytest.param(
            'try: ...\n'
            'except WindowsError: ...\n',

            'try: ...\n'
            'except OSError: ...\n',

            id='except of name',
        ),
        pytest.param(
            'try: ...\n'
            'except os.error: ...\n',

            'try: ...\n'
            'except OSError: ...\n',

            id='except of dotted name',
        ),
        pytest.param(
            'try: ...\n'
            'except (WindowsError,): ...\n',

            'try: ...\n'
            'except OSError: ...\n',

            id='except of name in tuple',
        ),
        pytest.param(
            'try: ...\n'
            'except (os.error,): ...\n',

            'try: ...\n'
            'except OSError: ...\n',

            id='except of dotted name in tuple',
        ),
        pytest.param(
            'try: ...\n'
            'except (WindowsError, KeyError, OSError): ...\n',

            'try: ...\n'
            'except (OSError, KeyError): ...\n',

            id='deduplicates exception types',
        ),
        pytest.param(
            'try: ...\n'
            'except (os.error, WindowsError, OSError): ...\n',

            'try: ...\n'
            'except OSError: ...\n',

            id='deduplicates to a single type',
        ),
        pytest.param(
            'try: ...\n'
            'except(os.error, WindowsError, OSError): ...\n',

            'try: ...\n'
            'except OSError: ...\n',

            id='deduplicates to a single type without whitespace',
        ),
        pytest.param(
            'from wat import error\n'
            'try: ...\n'
            'except (WindowsError, error): ...\n',

            'from wat import error\n'
            'try: ...\n'
            'except (OSError, error): ...\n',

            id='leave unrelated error names alone',
        ),
    ),
)
def test_fix_exceptions(s, expected):
    assert _fix_plugins(s, settings=Settings()) == expected


@pytest.mark.parametrize(
    ('s', 'expected', 'version'),
    (
        pytest.param(
            'raise socket.timeout(1)\n',
            'raise TimeoutError(1)\n',
            (3, 10),
            id='socket.timeout',
        ),
        pytest.param(
            'raise asyncio.TimeoutError(1)\n',
            'raise TimeoutError(1)\n',
            (3, 11),
            id='asyncio.TimeoutError',
        ),
    ),
)
def test_fix_exceptions_versioned(s, expected, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == expected


def test_can_rewrite_disparate_names():
    s = '''\
try: ...
except (asyncio.TimeoutError, WindowsError): ...
'''
    expected = '''\
try: ...
except (TimeoutError, OSError): ...
'''

    assert _fix_plugins(s, settings=Settings(min_version=(3, 11))) == expected
