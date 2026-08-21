from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '@pytest.mark.skipif(some_condition, reason="something")\n'
            'def test(): pass\n',
            id='unrelated condition',
        ),
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            '@pytest.mark.skipif(six.PY2, reason="py3+")\n'
            'def test(): pass\n',

            'def test(): pass\n',

            id='test decorator',
        ),
        pytest.param(
            '@pytest.mark.skipif(six.PY2, reason="py3+")\n'
            'async def test(): pass\n',

            'async def test(): pass\n',

            id='async test decorator',
        ),
        pytest.param(
            '@pytest.mark.skipif(six.PY2, reason="py3+")\n'
            'class TestClass:\n'
            '    def test(self): pass\n',

            'class TestClass:\n'
            '    def test(self): pass\n',

            id='class decorator',
        ),
        pytest.param(
            '@pytest.mark.skipif(sys.version_info < (3, 6), reason="py36+")\n'
            'def test(): pass\n',

            'def test(): pass\n',

            id='versioned condition',
        ),
    ),
)
def test_fix_remove_decorator(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == expected
