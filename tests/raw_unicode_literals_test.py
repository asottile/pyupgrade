import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param('ur"hi"', 'u"hi"', id='basic case'),
        pytest.param('UR"hi"', 'U"hi"', id='upper case raw'),
        pytest.param(r'ur"\s"', r'u"\\s"', id='with an escape'),
        pytest.param('ur"\\u2603"', 'u"\\u2603"', id='with unicode escapes'),
        pytest.param('ur"\\U0001f643"', 'u"\\U0001f643"', id='emoji'),
    ),
)
def test_fix_ur_literals(s, expected):
    assert _fix_tokens(s, min_version=(2, 7)) == expected


def test_fix_ur_literals_gets_fixed_before_u_removed():
    assert _fix_tokens("ur'\\s\\u2603'", min_version=(3,)) == "'\\\\s\\u2603'"
