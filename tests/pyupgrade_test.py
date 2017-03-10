# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import io

import pytest

from pyupgrade import _fix_format_literals
from pyupgrade import _fix_sets
from pyupgrade import _fix_unicode_literals
from pyupgrade import _imports_unicode_literals
from pyupgrade import parse_format
from pyupgrade import main
from pyupgrade import Token
from pyupgrade import tokenize_src
from pyupgrade import unparse_parsed_string
from pyupgrade import untokenize_tokens


@pytest.mark.parametrize(
    's',
    (
        '', 'foo', '{}', '{0}', '{named}', '{!r}', '{:>5}', '{{', '}}',
        '{0!s:15}'
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


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # Don't touch empty set literals
        ('set()', 'set()'),
        # Don't touch set(empty literal) with newlines in them (may create
        # syntax errors)
        ('set((\n))', 'set((\n))'),
        # Don't touch weird looking function calls -- use autopep8 or such
        # first
        ('set (())', 'set (())'),
        ('set ((1, 2))', 'set ((1, 2))'),
        # Take a set literal with an empty tuple / list and remove the arg
        ('set(())', 'set()'),
        ('set([])', 'set()'),
        # Remove spaces in empty set literals
        ('set(( ))', 'set()'),
        # Some "normal" test cases
        ('set((1, 2))', '{1, 2}'),
        ('set([1, 2])', '{1, 2}'),
        ('set(x for x in y)', '{x for x in y}'),
        ('set([x for x in y])', '{x for x in y}'),
        # These are strange cases -- the ast doesn't tell us about the parens
        # here so we have to parse ourselves
        ('set((x for x in y))', '{x for x in y}'),
        ('set(((1, 2)))', '{1, 2}'),
        # Some multiline cases
        ('set(\n(1, 2))', '{\n1, 2}'),
        ('set((\n1,\n2,\n))\n', '{\n1,\n2,\n}\n'),
        # Nested sets
        (
            'set((frozenset(set((1, 2))), frozenset(set((3, 4)))))',
            '{frozenset({1, 2}), frozenset({3, 4})}',
        ),
        # Remove trailing commas on inline things
        ('set((1,))', '{1}'),
        ('set((1, ))', '{1}'),
    ),
)
def test_sets(s, expected):
    ret = _fix_sets(s)
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # Don't touch py27 format strings
        ("'{}'.format(1)", "'{}'.format(1)"),
        # Don't touch invalid format strings
        ("'{'.format(1)", "'{'.format(1)"),
        ("'}'.format(1)", "'}'.format(1)"),
        # Don't touch non-format strings
        ("x = ('{0} {1}',)\n", "x = ('{0} {1}',)\n"),
        # Simplest case
        ("'{0}'.format(1)", "'{}'.format(1)"),
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
    ),
)
def test_format_literals(s, expected):
    ret = _fix_format_literals(s)
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('import x', False),
        ('from foo import bar', False),
        ('x = 5', False),
        ('from __future__ import unicode_literals', True),
        (
            '"""docstring"""\n'
            'from __future__ import unicode_literals',
            True,
        ),
        (
            'from __future__ import absolute_import\n'
            'from __future__ import unicode_literals\n',
            True,
        ),
    ),
)
def test_imports_unicode_literals(s, expected):
    assert _imports_unicode_literals(s) is expected


@pytest.mark.parametrize(
    ('s', 'py3_only', 'expected'),
    (
        # Syntax errors are unchanged
        ('(', False, '('),
        # Without py3-only, no replacements
        ("u''", False, "u''"),
        # With py3-only, it removes u prefix
        ("u''", True, "''"),
        # Importing unicode_literals also cause it to remove it
        (
            'from __future__ import unicode_literals\n'
            'u""\n',
            False,
            'from __future__ import unicode_literals\n'
            '""\n',
        ),
    ),
)
def test_unicode_literals(s, py3_only, expected):
    ret = _fix_unicode_literals(s, py3_only=py3_only)
    assert ret == expected


def test_main_trivial():
    assert main(()) == 0


def test_main_noop(tmpdir):
    f = tmpdir.join('f.py')
    f.write('x = 5\n')
    assert main((f.strpath,)) == 0
    assert f.read() == 'x = 5\n'


def test_main_changes_a_file(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('x = set((1, 2, 3))\n')
    assert main((f.strpath,)) == 1
    out, _ = capsys.readouterr()
    assert out == 'Rewriting {}\n'.format(f.strpath)
    assert f.read() == 'x = {1, 2, 3}\n'


def test_main_syntax_error(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from __future__ import print_function\nprint 1\n')
    assert main((f.strpath,)) == 0


def test_main_non_utf8_bytes(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary('# -*- coding: cp1252 -*-\nx = €\n'.encode('cp1252'))
    assert main((f.strpath,)) == 1
    out, _ = capsys.readouterr()
    assert out == '{} is non-utf-8 (not supported)\n'.format(f.strpath)


def test_py3_only_argument_unicode_literals(tmpdir):
    f = tmpdir.join('f.py')
    f.write('u""')
    assert main((f.strpath,)) == 0
    assert f.read() == 'u""'
    assert main((f.strpath, '--py3-only')) == 1
    assert f.read() == '""'
