# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pyupgrade import _fix_tokens
from pyupgrade import _imports_unicode_literals


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('', False),
        ('import x', False),
        ('from foo import bar', False),
        ('x = 5', False),
        ('from __future__ import unicode_literals', True),
        (
            '"""docstring"""\n'
            'from __future__ import unicode_literals',
            True,
        ),
        (
            'from __future__ import absolute_import\n'
            'from __future__ import unicode_literals\n',
            True,
        ),
    ),
)
def test_imports_unicode_literals(s, expected):
    assert _imports_unicode_literals(s) is expected


@pytest.mark.parametrize(
    ('s', 'py3_plus'),
    (
        # Syntax errors are unchanged
        ('(', False),
        # Without py3-plus, no replacements
        ("u''", False),
        # Regression: string containing newline
        ('"""with newline\n"""', True),
        pytest.param(
            'def f():\n'
            '    return"foo"\n',
            True,
            id='Regression: no space between return and string',
        ),
    ),
)
def test_unicode_literals_noop(s, py3_plus):
    assert _fix_tokens(s, py3_plus=py3_plus) == s


@pytest.mark.parametrize(
    ('s', 'py3_plus', 'expected'),
    (
        # With py3-plus, it removes u prefix
        ("u''", True, "''"),
        # Importing unicode_literals also cause it to remove it
        (
            'from __future__ import unicode_literals\n'
            'u""\n',
            False,
            'from __future__ import unicode_literals\n'
            '""\n',
        ),
    ),
)
def test_unicode_literals(s, py3_plus, expected):
    ret = _fix_tokens(s, py3_plus=py3_plus)
    assert ret == expected
