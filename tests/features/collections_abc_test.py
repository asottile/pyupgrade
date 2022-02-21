from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'import contextlib, collections, sys\n',
            id='does not rewrite multiple imports',
        ),
        pytest.param(
            'from collections import Generator, defaultdict\n',
            id='does not rewrite imports with mix of abc and concrete',
        ),
        pytest.param(
            'from .collections import Generator\n',
            id='leave relative imports alone',
        ),
        pytest.param(
            'from collections.abc import Generator\n',
            id='leave already modified alone',
        ),
    ),
)
def test_collections_abc_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from collections import Generator\n'
            '\n'
            'isinstance(g, Generator)',
            'from collections.abc import Generator\n'
            '\n'
            'isinstance(g, Generator)',
            id='relative import class',
        ),
        pytest.param(
            'from collections import Generator, Awaitable, KeysView\n'
            '\n'
            'isinstance(g, collections.Generator)\n'
            'isinstance(a, collections.Awaitable)\n'
            'isinstance(kv, collections.KeysView)\n',
            'from collections.abc import Generator, Awaitable, KeysView\n'
            '\n'
            'isinstance(g, collections.Generator)\n'
            'isinstance(a, collections.Awaitable)\n'
            'isinstance(kv, collections.KeysView)\n',
            id='multiple relative import classes',
        ),
    ),
)
def test_fix_collections_abc_imports(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == expected
