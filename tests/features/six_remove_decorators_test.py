from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            '@six.python_2_unicode_compatible\n'
            'class C: pass',

            'class C: pass',
        ),
        (
            '@six.python_2_unicode_compatible\n'
            '@other_decorator\n'
            'class C: pass',

            '@other_decorator\n'
            'class C: pass',
        ),
        pytest.param(
            '@  six.python_2_unicode_compatible\n'
            'class C: pass\n',

            'class C: pass\n',

            id='weird spacing at the beginning python_2_unicode_compatible',
        ),
        (
            'from six import python_2_unicode_compatible\n'
            '@python_2_unicode_compatible\n'
            'class C: pass',

            'from six import python_2_unicode_compatible\n'
            'class C: pass',
        ),
    ),
)
def test_fix_six_remove_decorators(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
