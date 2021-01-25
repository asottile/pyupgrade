import pytest

from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # already a reduced mode
        'open("foo", "w")',
        'open("foo", "rb")',
        # nonsense mode
        'open("foo", "Uw")',
        # TODO: could maybe be rewritten to remove t?
        'open("foo", "wt")',
        # don't remove this, they meant to use `encoding=`
        'open("foo", "r", "utf-8")',
    ),
)
def test_fix_open_mode_noop(s):
    assert _fix_plugins(s, min_version=(3,), keep_percent_format=False) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('open("foo", "U")', 'open("foo")'),
        ('open("foo", "Ur")', 'open("foo")'),
        ('open("foo", "Ub")', 'open("foo", "rb")'),
        ('open("foo", "rUb")', 'open("foo", "rb")'),
        ('open("foo", "r")', 'open("foo")'),
        ('open("foo", "rt")', 'open("foo")'),
        ('open("f", "r", encoding="UTF-8")', 'open("f", encoding="UTF-8")'),
    ),
)
def test_fix_open_mode(s, expected):
    ret = _fix_plugins(s, min_version=(3,), keep_percent_format=False)
    assert ret == expected
