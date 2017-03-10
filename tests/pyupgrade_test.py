from __future__ import absolute_import
from __future__ import unicode_literals

import io

import pytest
import six

from pyupgrade import parse_format
from pyupgrade import Token
from pyupgrade import tokenize_src
from pyupgrade import unparse_parsed_string
from pyupgrade import untokenize_tokens


def _test_roundtrip(s):
    ret = unparse_parsed_string(parse_format(s))
    assert type(ret) is type(s)
    assert ret == s


xfailpy3 = pytest.mark.xfail(
    six.PY3, reason='PY3: no bytes formatting', strict=True,
)


CASES = (
    '', 'foo', '{}', '{0}', '{named}', '{!r}', '{:>5}', '{{', '}}',
    '{0!s:15}',
)
CASES_BYTES = tuple(x.encode('UTF-8') for x in CASES)


@pytest.mark.parametrize('s', CASES)
def test_roundtrip_text(s):
    _test_roundtrip(s)


@xfailpy3
@pytest.mark.parametrize('s', CASES_BYTES)
def test_roundtrip_bytes(s):
    _test_roundtrip(s)


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('{:}', '{}'),
        ('{0:}', '{0}'),
        ('{0!r:}', '{0!r}'),
    ),
)
def test_intentionally_not_round_trip(s, expected):
    # Our unparse simplifies empty parts, whereas stdlib allows them
    ret = unparse_parsed_string(parse_format(s))
    assert ret == expected


def test_tokenize_src_simple():
    src = 'x = 5\n'
    ret = tokenize_src(src)
    assert ret == [
        Token('NAME', 'x', line=1, utf8_byte_offset=0),
        Token('UNIMPORTANT_WS', ' ', line=None, utf8_byte_offset=None),
        Token('OP', '=', line=1, utf8_byte_offset=2),
        Token('UNIMPORTANT_WS', ' ', line=None, utf8_byte_offset=None),
        Token('NUMBER', '5', line=1, utf8_byte_offset=4),
        Token('NEWLINE', '\n', line=1, utf8_byte_offset=5),
        Token('ENDMARKER', '', line=2, utf8_byte_offset=0),
    ]


@pytest.mark.parametrize(
    'filename',
    (
        'testing/resources/empty.py',
        'testing/resources/unicode_snowman.py',
        'testing/resources/docstring.py',
        'testing/resources/backslash_continuation.py',
    ),
)
def test_roundtrip_tokenize(filename):
    with io.open(filename) as f:
        contents = f.read()
    ret = untokenize_tokens(tokenize_src(contents))
    assert ret == contents
