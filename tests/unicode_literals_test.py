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
    ('s', 'min_version'),
    (
        # Syntax errors are unchanged
        ('(', (2, 7)),
        # Without py3-plus, no replacements
        ("u''", (2, 7)),
        # Regression: string containing newline
        ('"""with newline\n"""', (3,)),
        pytest.param(
            'def f():\n'
            '    return"foo"\n',
            (3,),
            id='Regression: no space between return and string',
        ),
    ),
)
def test_unicode_literals_noop(s, min_version):
    assert _fix_tokens(s, min_version=min_version) == s


@pytest.mark.parametrize(
    ('s', 'min_version', 'expected'),
    (
        # With py3-plus, it removes u prefix
        ("u''", (3,), "''"),
        # Importing unicode_literals also cause it to remove it
        (
            'from __future__ import unicode_literals\n'
            'u""\n',
            (2, 7),
            'from __future__ import unicode_literals\n'
            '""\n',
        ),
    ),
)
def test_unicode_literals(s, min_version, expected):
    assert _fix_tokens(s, min_version=min_version) == expected
