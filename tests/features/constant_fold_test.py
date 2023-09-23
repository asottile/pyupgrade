from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'isinstance(x, str)',
            id='isinstance nothing duplicated',
        ),
        pytest.param(
            'issubclass(x, str)',
            id='issubclass nothing duplicated',
        ),
        pytest.param(
            'try: ...\n'
            'except Exception: ...\n',
            id='try-except nothing duplicated',
        ),
        pytest.param(
            'isinstance(x, (str, (str,)))',
            id='only consider flat tuples',
        ),
        pytest.param(
            'isinstance(x, (f(), a().g))',
            id='only consider names and dotted names',
        ),
    ),
)
def test_constant_fold_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'isinstance(x, (str, str, int))',

            'isinstance(x, (str, int))',

            id='isinstance',
        ),
        pytest.param(
            'issubclass(x, (str, str, int))',

            'issubclass(x, (str, int))',

            id='issubclass',
        ),
        pytest.param(
            'try: ...\n'
            'except (Exception, Exception, TypeError): ...\n',

            'try: ...\n'
            'except (Exception, TypeError): ...\n',

            id='except',
        ),

        pytest.param(
            'isinstance(x, (str, str))',

            'isinstance(x, str)',

            id='folds to 1',
        ),

        pytest.param(
            'isinstance(x, (a.b, a.b, a.c))',
            'isinstance(x, (a.b, a.c))',
            id='folds dotted names',
        ),
        pytest.param(
            'try: ...\n'
            'except(a, a): ...\n',

            'try: ...\n'
            'except a: ...\n',

            id='deduplication to 1 does not cause syntax error with except',
        ),
    ),
)
def test_constant_fold(s, expected):
    assert _fix_plugins(s, settings=Settings()) == expected
