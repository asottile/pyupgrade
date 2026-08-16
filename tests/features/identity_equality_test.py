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
        'x is ...',
        'x is (not 5)',
        'x is 5 + 5',
        # pyupgrade is timid about mutable containers since the original can be
        # always-False, but the rewritten code could be `True`.
        'x is []',
        'x is {}',
        'x is {1}',
        # Tuple with a non-constants is also always-False.
        'x is ([1,2,3],)',
        'x is ((1,2,3),)',
    ),
)
def test_fix_is_compare_to_literal_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param('x is 5', 'x == 5', id='`is`'),
        pytest.param('x is not 5', 'x != 5', id='`is not`'),
        pytest.param('5 is x', '5 == x', id='literal on the left'),
        pytest.param('x is ""', 'x == ""', id='string'),
        pytest.param('x is u""', 'x == u""', id='unicode string'),
        pytest.param('x is b""', 'x == b""', id='bytes'),
        pytest.param('x is 1.5', 'x == 1.5', id='float'),
        pytest.param('x is 2j', 'x == 2j', id='complex'),
        pytest.param('x is (1,2,3)', 'x == (1,2,3)', id='tuple'),
        pytest.param('x is (None,)', 'x == (None,)', id='tuple with None'),
        pytest.param('x is (True, 1)', 'x == (True, 1)', id='tuple with bool'),
        pytest.param('x is (...,)', 'x == (...,)', id='tuple with ellipsis'),
        # Regression tests - ensure we don't mistake those cases for `x is True`.
        pytest.param('x is 1', 'x == 1', id='int equals bool True'),
        pytest.param('x is 1.0', 'x == 1.0', id='float equals bool True'),
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
