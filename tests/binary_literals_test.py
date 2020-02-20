import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        '"☃".encode("UTF-8")',
        '"\\u2603".encode("UTF-8")',
        '"\\U0001f643".encode("UTF-8")',
        '"\\N{SNOWMAN}".encode("UTF-8")',
        '"\\xa0".encode("UTF-8")',
        # not byte literal compatible
        '"y".encode("utf16")',
        # can't rewrite f-strings
        'f"{x}".encode()',
        # not a `.encode()` call
        '"foo".encode', '("foo".encode)',
        # encode, but not a literal
        'x.encode()',
        # the codec / string is an f-string
        'str.encode(f"{c}")', '"foo".encode(f"{c}")',
    ),
)
def test_binary_literals_noop(s):
    assert _fix_tokens(s, min_version=(2, 7)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('"foo".encode()', 'b"foo"'),
        ('"foo".encode("ascii")', 'b"foo"'),
        ('"foo".encode("utf-8")', 'b"foo"'),
        ('"\\xa0".encode("latin1")', 'b"\\xa0"'),
        (r'"\\u wot".encode()', r'b"\\u wot"'),
        (r'"\\x files".encode()', r'b"\\x files"'),
        (
            'f(\n'
            '    "foo"\n'
            '    "bar".encode()\n'
            ')\n',

            'f(\n'
            '    b"foo"\n'
            '    b"bar"\n'
            ')\n',
        ),
        (
            'f(\n'
            '    U"foo"\n'
            '    ur"bar".encode()\n'
            ')\n',

            'f(\n'
            '    b"foo"\n'
            '    br"bar"\n'
            ')\n',
        ),
    ),
)
def test_binary_literals(s, expected):
    assert _fix_tokens(s, min_version=(2, 7)) == expected
