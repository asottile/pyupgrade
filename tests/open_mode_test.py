import pytest

from pyupgrade import _fix_py3_plus


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
    ),
)
def test_fix_open_mode_noop(s):
    assert _fix_py3_plus(s) == s


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
    assert _fix_py3_plus(s) == expected
