import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('5L', '5'),
        ('5l', '5'),
        ('123456789123456789123456789L', '123456789123456789123456789'),
    ),
)
def test_long_literals(s, expected):
    assert _fix_tokens(s, min_version=(2, 7)) == expected
