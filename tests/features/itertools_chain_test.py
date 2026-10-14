from __future__ import annotations

import itertools
import sys

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_noop_before_315():
    s = 'itertools.chain.from_iterable(x)'
    assert _fix_plugins(s, settings=Settings(min_version=(3, 14))) == s


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'itertools.chain.from_iterable(it=x)',
            id='from_iterable named argument',
        ),
        pytest.param(
            'itertools.chain.from_iterable(*x)',
            id='from_iterable starred argument',
        ),
        pytest.param(
            'itertools.chain(it=x)',
            id='chain named argument',
        ),
        pytest.param(
            'itertools.chain.from_iterable(rows := other)',
            id='from_iterable assignment expression',
        ),
        pytest.param(
            'itertools.chain(*(rows := other))',
            id='chain starred assignment expression',
        ),
        pytest.param(
            'itertools.chain((rows := other), rows)',
            id='chain multiple arguments assignment expression',
        ),
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 15))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'itertools.chain.from_iterable(x)',
            '(*it for it in x)',
            id='from_iterable',
        ),
        pytest.param(
            'itertools.chain.from_iterable(row for row in rows)',
            '(*it for it in (row for row in rows))',
            id='from_iterable generator expression',
        ),
        pytest.param(
            'itertools.chain.from_iterable(\n'
            '    row for row in rows  # comment\n'
            ')',
            '(*it for it in (\n'
            '    row for row in rows  # comment\n'
            '))',
            id='from_iterable multiline generator expression',
        ),
        pytest.param(
            'itertools.chain.from_iterable(rows if flag else other)',
            '(*it for it in (rows if flag else other))',
            id='from_iterable conditional expression',
        ),
        pytest.param(
            'itertools.chain(*rows if flag else other)',
            '(*it for it in (rows if flag else other))',
            id='chain starred conditional expression',
        ),
        pytest.param(
            'itertools.chain(*x)',
            '(*it for it in x)',
            id='chain, one star arg',
        ),
        pytest.param(
            'itertools.chain( *x )',
            '(*it for it in x)',
            id='chain star with whitespace',
        ),
        pytest.param(
            'itertools.chain(*x, *y)',
            '(*it for it in (*x, *y))',
            id='chain, multiple starred',
        ),
        pytest.param(
            'itertools.chain(a, b, c)',
            '(*it for it in (a, b, c))',
            id='chain, multiple arguments',
        ),
        pytest.param(
            'from itertools import chain\n'
            'chain.from_iterable(x)\n',

            'from itertools import chain\n'
            '(*it for it in x)\n',

            id='from import',
        ),
        pytest.param(
            'itertools.chain(x)\n',
            'iter(x)\n',
            id='single arg to iter',
        ),
        pytest.param(
            'itertools.chain(\n'
            '    x,\n'
            '    # comment\n'
            ')\n',

            'iter(x)\n',

            id='comment after single arg',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert ret == expected


@pytest.mark.skipif(
    sys.version_info < (3, 15), reason='comprehension unpacking',
)
@pytest.mark.parametrize('flag', [True, False])
@pytest.mark.parametrize(
    's', [
        'itertools.chain.from_iterable(row for row in rows)',
        'itertools.chain.from_iterable(\n'
        '    row for row in rows  # comment\n'
        ')',
        'itertools.chain.from_iterable(rows if flag else other)',
        'itertools.chain(*rows if flag else other)',
    ],
)
def test_rewrite_preserves_values(s, flag):
    namespace = {
        'itertools': itertools,
        'rows': [[1, 2], [3]],
        'other': [[4, 5]],
        'flag': flag,
    }
    expected = list(eval(s, namespace))
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert list(eval(ret, namespace)) == expected
