from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        'x.__aiter__()',
        'x.__anext__()',
    ),
)
def test_noop_pre_3_10(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 9))) == s


@pytest.mark.parametrize(
    's',
    (
        # no call
        'x.__aiter__',
        'x.__anext__',
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 10))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param('x.__aiter__()', 'aiter(x)', id='aiter'),
        pytest.param('x.__anext__()', 'anext(x)', id='anext'),
        pytest.param(
            'x.__anext__(  )',
            'anext(x)',
            id='whitespace inside empty call',
        ),
        pytest.param(
            '(x async for x in y).__anext__()',
            'anext((x async for x in y))',
            id='async generator',
        ),
        pytest.param(
            'a.b().__anext__()',
            'anext(a.b())',
            id='attribute-call chain',
        ),
        pytest.param(
            '(await x.__anext__()).__anext__()',
            'anext((await anext(x)))',
            id='nested dunder call',
        ),
        pytest.param(
            'await a.__aiter__().__anext__()',
            'await anext(aiter(a))',
            id='chained aiter and anext',
        ),
        pytest.param(
            '(x async for x in y if x.__anext__ is not None).__anext__()',
            'anext((x async for x in y if x.__anext__ is not None))',
            id='unrelated bare dunder attribute',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 10)))
    assert ret == expected
