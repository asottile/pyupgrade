# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pyupgrade import _fix_format_literals
from pyupgrade import parse_format
from pyupgrade import unparse_parsed_string


@pytest.mark.parametrize(
    's',
    (
        '', 'foo', '{}', '{0}', '{named}', '{!r}', '{:>5}', '{{', '}}',
        '{0!s:15}',
    ),
)
def test_roundtrip_text(s):
    assert unparse_parsed_string(parse_format(s)) == s


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


@pytest.mark.parametrize(
    's',
    (
        # Don't touch syntax errors
        '"{0}"format(1)',
        # Don't touch py27 format strings
        "'{}'.format(1)",
        # Don't touch invalid format strings
        "'{'.format(1)", "'}'.format(1)",
        # Don't touch non-format strings
        "x = ('{0} {1}',)\n",
        # Don't touch non-incrementing integers
        "'{0} {0}'.format(1)",
        # Formats can be embedded in formats, leave these alone?
        "'{0:<{1}}'.format(1, 4)",
    ),
)
def test_format_literals_noop(s):
    assert _fix_format_literals(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # Simplest case
        ("'{0}'.format(1)", "'{}'.format(1)"),
        ("'{0:x}'.format(30)", "'{:x}'.format(30)"),
        ("x = '{0}'.format(1)", "x = '{}'.format(1)"),
        # Multiline strings
        ("'''{0}\n{1}\n'''.format(1, 2)", "'''{}\n{}\n'''.format(1, 2)"),
        # Multiple implicitly-joined strings
        ("'{0}' '{1}'.format(1, 2)", "'{}' '{}'.format(1, 2)"),
        # Multiple implicitly-joined strings over lines
        (
            'print(\n'
            "    'foo{0}'\n"
            "    'bar{1}'.format(1, 2)\n"
            ')',
            'print(\n'
            "    'foo{}'\n"
            "    'bar{}'.format(1, 2)\n"
            ')',
        ),
        # Multiple implicitly-joind strings over lines with comments
        (
            'print(\n'
            "    'foo{0}'  # ohai\n"
            "    'bar{1}'.format(1, 2)\n"
            ')',
            'print(\n'
            "    'foo{}'  # ohai\n"
            "    'bar{}'.format(1, 2)\n"
            ')',
        ),
        # joined by backslash
        (
            'x = "foo {0}" \\\n'
            '    "bar {1}".format(1, 2)',
            'x = "foo {}" \\\n'
            '    "bar {}".format(1, 2)',
        ),
    ),
)
def test_format_literals(s, expected):
    ret = _fix_format_literals(s)
    assert ret == expected
