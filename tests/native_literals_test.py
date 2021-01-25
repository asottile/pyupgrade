import pytest

from pyupgrade._main import _fix_plugins


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
    assert _fix_plugins(s, min_version=(3,), keep_percent_format=False) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('str()', "''"),
        ('str("foo")', '"foo"'),
        ('str("""\nfoo""")', '"""\nfoo"""'),
        ('six.ensure_str("foo")', '"foo"'),
        ('six.ensure_text("foo")', '"foo"'),
        ('six.text_type("foo")', '"foo"'),
        pytest.param(
            'from six import text_type\n'
            'text_type("foo")\n',

            'from six import text_type\n'
            '"foo"\n',

            id='from import of rewritten name',
        ),
    ),
)
def test_fix_native_literals(s, expected):
    ret = _fix_plugins(s, min_version=(3,), keep_percent_format=False)
    assert ret == expected
