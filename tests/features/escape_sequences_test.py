from __future__ import annotations

import pytest

from pyupgrade._main import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        '""',
        r'r"\d"', r"r'\d'", r'r"""\d"""', r"r'''\d'''",
        r'rb"\d"',
        # make sure we don't replace an already valid string
        r'"\\d"',
        # this is already a proper unicode escape
        r'"\u2603"',
        # don't touch already valid escapes
        r'"\r\n"',
        # python3.3+ named unicode escapes
        r'"\N{SNOWMAN}"',
        # don't touch escaped newlines
        '"""\\\n"""', '"""\\\r\n"""', '"""\\\r"""',
    ),
)
def test_fix_escape_sequences_noop(s):
    assert _fix_tokens(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # no valid escape sequences, make a raw literal
        (r'"\d"', r'r"\d"'),
        # when there are valid escape sequences, need to use backslashes
        (r'"\n\d"', r'"\n\\d"'),
        # this gets un-u'd and raw'd
        (r'u"\d"', r'r"\d"'),
        # `rb` is not a valid string prefix in python2.x
        (r'b"\d"', r'br"\d"'),
        # 8 and 9 aren't valid octal digits
        (r'"\8"', r'r"\8"'), (r'"\9"', r'r"\9"'),
        # explicit byte strings should not honor string-specific escapes
        ('b"\\u2603"', 'br"\\u2603"'),
        # do not make a raw string for escaped newlines
        ('"""\\\n\\q"""', '"""\\\n\\\\q"""'),
        ('"""\\\r\n\\q"""', '"""\\\r\n\\\\q"""'),
        ('"""\\\r\\q"""', '"""\\\r\\\\q"""'),
        # python2.x allows \N, in python3.3+ this is a syntax error
        (r'"\N"', r'r"\N"'), (r'"\N\n"', r'"\\N\n"'),
        (r'"\N{SNOWMAN}\q"', r'"\N{SNOWMAN}\\q"'),
        (r'b"\N{SNOWMAN}"', r'br"\N{SNOWMAN}"'),
    ),
)
def test_fix_escape_sequences(s, expected):
    assert _fix_tokens(s) == expected
