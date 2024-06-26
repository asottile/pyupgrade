from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'from collections.abc import Generator\n'
            'def f() -> Generator[int, None, None]: yield 1\n',
            (3, 12),
            id='not 3.13+, no __future__.annotations',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from collections.abc import Generator\n'
            'def f() -> Generator[int]: yield 1\n',
            (3, 12),
            id='already converted!',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from collections.abc import Generator\n'
            'def f() -> Generator[int, int, None]: yield 1\n'
            'def g() -> Generator[int, int, int]: yield 1\n',
            (3, 12),
            id='non-None send/return type',
        ),
    ),
)
def test_fix_pep696_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


def test_fix_pep696_noop_keep_runtime_typing():
    settings = Settings(min_version=(3, 12), keep_runtime_typing=True)
    s = '''\
from __future__ import annotations
from collections.abc import Generator
def f() -> Generator[int, None, None]: yield 1
'''
    assert _fix_plugins(s, settings=settings) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from __future__ import annotations\n'
            'from typing import Generator\n'
            'def f() -> Generator[int, None, None]: yield 1\n',

            'from __future__ import annotations\n'
            'from collections.abc import Generator\n'
            'def f() -> Generator[int]: yield 1\n',

            id='typing.Generator',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from typing_extensions import Generator\n'
            'def f() -> Generator[int, None, None]: yield 1\n',

            'from __future__ import annotations\n'
            'from typing_extensions import Generator\n'
            'def f() -> Generator[int]: yield 1\n',

            id='typing_extensions.Generator',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from collections.abc import Generator\n'
            'def f() -> Generator[int, None, None]: yield 1\n',

            'from __future__ import annotations\n'
            'from collections.abc import Generator\n'
            'def f() -> Generator[int]: yield 1\n',

            id='collections.abc.Generator',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from collections.abc import AsyncGenerator\n'
            'async def f() -> AsyncGenerator[int, None]: yield 1\n',

            'from __future__ import annotations\n'
            'from collections.abc import AsyncGenerator\n'
            'async def f() -> AsyncGenerator[int]: yield 1\n',

            id='collections.abc.AsyncGenerator',
        ),
    ),
)
def test_fix_pep696_with_future_annotations(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 12))) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from collections.abc import Generator\n'
            'def f() -> Generator[int, None, None]: yield 1\n',

            'from collections.abc import Generator\n'
            'def f() -> Generator[int]: yield 1\n',

            id='Generator',
        ),
        pytest.param(
            'from collections.abc import AsyncGenerator\n'
            'async def f() -> AsyncGenerator[int, None]: yield 1\n',

            'from collections.abc import AsyncGenerator\n'
            'async def f() -> AsyncGenerator[int]: yield 1\n',

            id='AsyncGenerator',
        ),
    ),
)
def test_fix_pep696_with_3_13(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 13))) == expected
