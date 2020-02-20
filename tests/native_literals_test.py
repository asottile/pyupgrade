import pytest

from pyupgrade import _fix_py3_plus


@pytest.mark.parametrize(
    's',
    (
        'str(1)',
        'str("foo"\n"bar")',  # creates a syntax error
        'str(*a)', 'str("foo", *a)',
        'str(**k)', 'str("foo", **k)',
        'str("foo", encoding="UTF-8")',
    ),
)
def test_fix_native_literals_noop(s):
    assert _fix_py3_plus(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('str()', "''"),
        ('str("foo")', '"foo"'),
        ('str("""\nfoo""")', '"""\nfoo"""'),
        ('six.ensure_str("foo")', '"foo"'),
        ('six.ensure_text("foo")', '"foo"'),
        ('six.text_type("foo")', '"foo"'),
    ),
)
def test_fix_native_literals(s, expected):
    assert _fix_py3_plus(s) == expected
