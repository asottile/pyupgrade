from __future__ import annotations

import pytest

from pyupgrade._main import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        # Don't touch syntax errors
        '"{0}"format(1)',
        pytest.param("'{}'.format(1)", id='already upgraded'),
        # Don't touch invalid format strings
        "'{'.format(1)", "'}'.format(1)",
        # Don't touch non-format strings
        "x = ('{0} {1}',)\n",
        # Don't touch non-incrementing integers
        "'{0} {0}'.format(1)",
        # Formats can be embedded in formats, leave these alone?
        "'{0:<{1}}'.format(1, 4)",
        # don't attempt to fix this, garbage in garbage out
        "'{' '0}'.format(1)",
        # comment looks like placeholder but is not!
        '("{0}" # {1}\n"{2}").format(1, 2, 3)',
        # don't touch f-strings (these are wrong but don't make it worse)
        'f"{0}".format(a)',
        # shouldn't touch the format spec
        r'"{}\N{SNOWMAN}".format("")',
    ),
)
def test_format_literals_noop(s):
    assert _fix_tokens(s) == s


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
        # parenthesized string literals
        ('("{0}").format(1)', '("{}").format(1)'),
        pytest.param(
            r'"\N{snowman} {0}".format(1)',
            r'"\N{snowman} {}".format(1)',
            id='named escape sequence',
        ),
    ),
)
def test_format_literals(s, expected):
    assert _fix_tokens(s) == expected
