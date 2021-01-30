import pytest

from pyupgrade._main import _imports_future


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
        ('from .__future__ import unicode_literals\n', False),
    ),
)
def test_imports_future(s, expected):
    assert _imports_future(s, 'unicode_literals') is expected


def test_imports_future_non_unicode_literals():
    src = 'from __future__ import with_statement'
    assert _imports_future(src, 'with_statement')
