from __future__ import annotations

import pytest

from pyupgrade._main import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        pytest.param('(', id='syntax errors are unchanged'),
        # Regression: string containing newline
        pytest.param('"""with newline\n"""', id='string containing newline'),
        pytest.param(
            'def f():\n'
            '    return"foo"\n',
            id='Regression: no space between return and string',
        ),
    ),
)
def test_unicode_literals_noop(s):
    assert _fix_tokens(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param("u''", "''", id='it removes u prefix'),
    ),
)
def test_unicode_literals(s, expected):
    assert _fix_tokens(s) == expected
