import pytest

from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # renaming things for weird reasons
        'from six import StringIO as text_type\n'
        'isinstance(s, text_type)\n',
        # parenthesized part of attribute
        '(\n'
        '    six\n'
        ').text_type(u)\n',
        pytest.param(
            'from .six import text_type\n'
            'isinstance("foo", text_type)\n',
            id='relative import might not be six',
        ),
    ),
)
def test_six_simple_noop(s):
    assert _fix_plugins(s, min_version=(3,), keep_percent_format=False) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'isinstance(s, six.text_type)',
            'isinstance(s, str)',
        ),
        pytest.param(
            'isinstance(s, six   .    string_types)',
            'isinstance(s, str)',
            id='weird spacing on six.attr',
        ),
        (
            'isinstance(s, six.string_types)',
            'isinstance(s, str)',
        ),
        (
            'issubclass(tp, six.string_types)',
            'issubclass(tp, str)',
        ),
        (
            'STRING_TYPES = six.string_types',
            'STRING_TYPES = (str,)',
        ),
        (
            'from six import string_types\n'
            'isinstance(s, string_types)\n',

            'from six import string_types\n'
            'isinstance(s, str)\n',
        ),
        (
            'from six import string_types\n'
            'STRING_TYPES = string_types\n',

            'from six import string_types\n'
            'STRING_TYPES = (str,)\n',
        ),
    ),
)
def test_fix_six_simple(s, expected):
    ret = _fix_plugins(s, min_version=(3,), keep_percent_format=False)
    assert ret == expected
