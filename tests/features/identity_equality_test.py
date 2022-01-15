from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        'x is True',
        'x is False',
        'x is None',
        'x is (not 5)',
        'x is 5 + 5',
        # pyupgrade is timid about containers since the original can be
        # always-False, but the rewritten code could be `True`.
        'x is ()',
        'x is []',
        'x is {}',
        'x is {1}',
    ),
)
def test_fix_is_compare_to_literal_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param('x is 5', 'x == 5', id='`is`'),
        pytest.param('x is not 5', 'x != 5', id='`is not`'),
        pytest.param('x is ""', 'x == ""', id='string'),
        pytest.param('x is u""', 'x == u""', id='unicode string'),
        pytest.param('x is b""', 'x == b""', id='bytes'),
        pytest.param('x is 1.5', 'x == 1.5', id='float'),
        pytest.param('x == 5 is 5', 'x == 5 == 5', id='compound compare'),
        pytest.param(
            'if (\n'
            '    x is\n'
            '    5\n'
            '): pass\n',

            'if (\n'
            '    x ==\n'
            '    5\n'
            '): pass\n',

            id='multi-line `is`',
        ),
        pytest.param(
            'if (\n'
            '    x is\n'
            '    not 5\n'
            '): pass\n',

            'if (\n'
            '    x != 5\n'
            '): pass\n',

            id='multi-line `is not`',
        ),
    ),
)
def test_fix_is_compare_to_literal(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
