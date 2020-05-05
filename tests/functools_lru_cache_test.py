import pytest

from pyupgrade import _fix_py3_plus


@pytest.mark.parametrize(
    ('s', 'min_version'),
    (
        pytest.param(
            'from functools import lru_cache as lru_cache2\n\n'
            '@lru_cache2()\n'
            'def foo():\n'
            '    pass\n',
            (3, 8),
            id='not following as imports',
        ),
        pytest.param(
            'from functools import lru_cache\n\n'
            '@lru_cache(max_size=1024)\n'
            'def foo():\n'
            '    pass\n',
            (3, 8),
            id='not rewriting calls with args',
        ),
        pytest.param(
            'from functools2 import lru_cache\n\n'
            '@lru_cache()\n'
            'def foo():\n'
            '    pass\n',
            (3, 8),
            id='not following unknown import',
        ),
        pytest.param(
            'from functools import lru_cache\n\n'
            '@lru_cache()\n'
            'def foo():\n'
            '    pass\n',
            (3,),
            id='not rewriting below 3.8',
        ),
        pytest.param(
            'from .functools import lru_cache\n'
            '@lru_cache()\n'
            'def foo(): pass\n',
            (3, 8),
            id='relative imports',
        ),
    ),
)
def test_fix_functools_lru_cache_noop(s, min_version):
    assert _fix_py3_plus(s, min_version) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from functools import lru_cache\n\n'
            '@lru_cache()\n'
            'def foo():\n'
            '    pass\n',
            'from functools import lru_cache\n\n'
            '@lru_cache\n'
            'def foo():\n'
            '    pass\n',
            id='call without attr',
        ),
        pytest.param(
            'import functools\n\n'
            '@functools.lru_cache()\n'
            'def foo():\n'
            '    pass\n',
            'import functools\n\n'
            '@functools.lru_cache\n'
            'def foo():\n'
            '    pass\n',
            id='call with attr',
        ),
    ),
)
def test_fix_functools_lru_cache(s, expected):
    assert _fix_py3_plus(s, (3, 8)) == expected
