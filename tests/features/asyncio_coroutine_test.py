import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.xfail
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import asyncio\n\n'
            '@asyncio.coroutine\n'
            'def foo():\n'
            '    pass\n',
            'async def foo():\n'
            '    pass\n',
            id='Convert to async',
        ),
    ),
)
def test_replace_coroutine_with_async_def(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 5)))
    assert ret == expected
