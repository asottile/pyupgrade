import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        # Any number of zeros is considered a legal token
        '0', '00',
        # Don't modify non octal literals
        '1', '12345', '1.2345', '1_005',
    ),
)
def test_noop_octal_literals(s):
    assert _fix_tokens(s, min_version=(2, 7)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('0755', '0o755'),
        ('05', '5'),
    ),
)
def test_fix_octal_literal(s, expected):
    assert _fix_tokens(s, min_version=(2, 7)) == expected
