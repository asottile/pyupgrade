from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected', 'version'),
    (
        pytest.param(
            'import socket\n'
            'raise socket.timeout("error")',

            'import socket\n'
            'raise TimeoutError("error")',

            (3, 10),

            id='rewriting socket.timeout',
        ),
        pytest.param(
            'from socket import timeout\n'
            'raise timeout("error")',

            'from socket import timeout\n'
            'raise TimeoutError("error")',

            (3, 10),

            id='rewriting timeout',
        ),
        pytest.param(
            'import asyncio\n'
            'raise asyncio.TimeoutError("error")',

            'import asyncio\n'
            'raise TimeoutError("error")',

            (3, 11),

            id='rewriting asyncio.TimeoutError',
        ),
        pytest.param(
            'from concurrent import futures\n'
            'raise futures.TimeoutError("error")',

            'from concurrent import futures\n'
            'raise TimeoutError("error")',

            (3, 11),

            id='rewriting futures.TimeoutError',
        ),
    ),
)
def test_fix_timeout_error_alias(s, expected, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == expected


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'import socket\n'
            'raise socket.timeout("error")',

            (3, 9),

            id='socket.timeout not Python 3.10+',
        ),
        pytest.param(
            'import foo\n'
            'raise foo.timeout("error")',

            (3, 10),

            id='timeout not from socket as attr',
        ),
        pytest.param(
            'from foo import timeout\n'
            'raise timeout("error")',

            (3, 10),

            id='timeout not from socket',
        ),
        pytest.param(
            'import asyncio\n'
            'raise asyncio.TimeoutError("error")',

            (3, 10),

            id='asyncio.TimeoutError not Python 3.11+',
        ),
        pytest.param(
            'from concurrent import futures\n'
            'raise futures.TimeoutError("error")',

            (3, 10),

            id='concurrent.futures.TimeoutError not Python 3.11+',
        ),
    ),
)
def test_fix_timeout_error_alias_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import asyncio\n'
            'try:\n'
            '    pass\n'
            'except asyncio.TimeoutError as e:\n'
            '    pass',

            'import asyncio\n'
            'try:\n'
            '    pass\n'
            'except TimeoutError as e:\n'
            '    pass',

            id='rewriting asyncio.TimeoutError in try/except',
        ),
    ),
)
def test_alias_in_try_except(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 11))) == expected
