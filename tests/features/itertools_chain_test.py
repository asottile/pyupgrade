from __future__ import annotations

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
