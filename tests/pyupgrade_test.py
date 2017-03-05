from __future__ import absolute_import
from __future__ import unicode_literals

import pytest
import six

from pyupgrade import parse_format
from pyupgrade import unparse_parsed_string


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
