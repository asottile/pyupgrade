# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import ast
import sys

import pytest

from pyupgrade_opt import _fix_dictcomps
from pyupgrade_opt import _fix_format_literals
from pyupgrade_opt import _fix_fstrings
from pyupgrade_opt import _fix_long_literals
from pyupgrade_opt import _fix_new_style_classes
from pyupgrade_opt import _fix_octal_literals
from pyupgrade_opt import _fix_percent_format
from pyupgrade_opt import _fix_sets
from pyupgrade_opt import _fix_six
from pyupgrade_opt import _fix_super
from pyupgrade_opt import _fix_unicode_literals
from pyupgrade_opt import _imports_unicode_literals
from pyupgrade_opt import _is_bytestring
from pyupgrade_opt import _percent_to_format
from pyupgrade_opt import _simplify_conversion_flag
from pyupgrade_opt import main
from pyupgrade_opt import parse_format
from pyupgrade_opt import parse_percent_format
from pyupgrade_opt import unparse_parsed_string


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
        # The ast also doesn't tell us about the start of the tuple in this
        # generator expression
        ('set((a, b) for a, b in y)', '{(a, b) for a, b in y}'),
        # The ast also doesn't tell us about the start of the tuple for
        # tuple of tuples
        ('set(((1, 2), (3, 4)))', '{(1, 2), (3, 4)}'),
        # Lists where the first element is a tuple also gives the ast trouble
        # The first element lies about the offset of the element
        ('set([(1, 2), (3, 4)])', '{(1, 2), (3, 4)}'),
        (
            'set(\n'
            '    [(1, 2)]\n'
            ')',
            '{\n'
            '    (1, 2)\n'
            '}',
        ),
        ('set([((1, 2)), (3, 4)])', '{((1, 2)), (3, 4)}'),
        # And it gets worse
        ('set((((1, 2),),))', '{((1, 2),)}'),
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
        # Remove trailing commas after things
        ('set([1, 2, 3,],)', '{1, 2, 3}'),
        ('set((x for x in y),)', '{x for x in y}'),
        (
            'set(\n'
            '    (x for x in y),\n'
            ')',
            '{\n'
            '    x for x in y\n'
            '}',
        ),
    ),
)
def test_sets(s, expected):
    ret = _fix_sets(s)
    assert ret == expected


@pytest.mark.xfail(sys.version_info >= (3, 7), reason='genexp trailing comma')
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('set(x for x in y,)', '{x for x in y}'),
        (
            'set(\n'
            '    x for x in y,\n'
            ')',
            '{\n'
            '    x for x in y\n'
            '}',
        ),
    ),
)
def test_sets_generators_trailing_comas(s, expected):
    ret = _fix_sets(s)
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # Don't touch irrelevant code
        ('x = 5', 'x = 5'),
        ('dict()', 'dict()'),
        # Don't touch syntax errors
        ('(', '('),
        # Don't touch strange looking calls
        ('dict ((a, b) for a, b in y)', 'dict ((a, b) for a, b in y)'),
        # dict of generator expression
        ('dict((a, b) for a, b in y)', '{a: b for a, b in y}'),
        ('dict((a, b,) for a, b in y)', '{a: b for a, b in y}'),
        ('dict((a, b, ) for a, b in y)', '{a: b for a, b in y}'),
        ('dict([a, b] for a, b in y)', '{a: b for a, b in y}'),
        # Parenthesized target
        ('dict(((a, b)) for a, b in y)', '{a: b for a, b in y}'),
        # dict of list comprehension
        ('dict([(a, b) for a, b in y])', '{a: b for a, b in y}'),
        # ast doesn't tell us about the tuple in the list
        ('dict([(a, b), c] for a, b, c in y)', '{(a, b): c for a, b, c in y}'),
        # ast doesn't tell us about parenthesized keys
        ('dict(((a), b) for a, b in y)', '{(a): b for a, b in y}'),
        # Nested dictcomps
        (
            'dict((k, dict((k2, v2) for k2, v2 in y2)) for k, y2 in y)',
            '{k: {k2: v2 for k2, v2 in y2} for k, y2 in y}',
        ),
        # This doesn't get fixed by autopep8 and can cause a syntax error
        ('dict((a, b)for a, b in y)', '{a: b for a, b in y}'),
        # Need to remove trailing commas on the element
        (
            'dict(\n'
            '    (\n'
            '        a,\n'
            '        b,\n'
            '    )\n'
            '    for a, b in y\n'
            ')',
            # Ideally, this'll go through some other formatting tool before
            # being committed.  Shrugs!
            '{\n'
            '        a:\n'
            '        b\n'
            '    for a, b in y\n'
            '}',
        ),
        # Don't rewrite kwargd dicts
        (
            'dict(((a, b) for a, b in y), x=1)',
            'dict(((a, b) for a, b in y), x=1)',
        ),
        (
            'dict(((a, b) for a, b in y), **kwargs)',
            'dict(((a, b) for a, b in y), **kwargs)',
        ),
        # Don't gobble the last paren in a dictcomp
        (
            'x(\n'
            '    dict(\n'
            '        (a, b) for a, b in y\n'
            '    )\n'
            ')',
            'x(\n'
            '    {\n'
            '        a: b for a, b in y\n'
            '    }\n'
            ')',
        )
    ),
)
def test_dictcomps(s, expected):
    ret = _fix_dictcomps(s)
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
        # Formats can be embedded in formats, leave these alone?
        ("'{0:<{1}}'.format(1, 4)", "'{0:<{1}}'.format(1, 4)"),
        # joined by backslash
        (
            'x = "foo {0}" \\\n'
            '    "bar {1}".format(1, 2)',
            'x = "foo {}" \\\n'
            '    "bar {}".format(1, 2)',
        )
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
    ('s', 'py3_plus', 'expected'),
    (
        # Syntax errors are unchanged
        ('(', False, '('),
        # Without py3-plus, no replacements
        ("u''", False, "u''"),
        # With py3-plus, it removes u prefix
        ("u''", True, "''"),
        # Importing unicode_literals also cause it to remove it
        (
            'from __future__ import unicode_literals\n'
            'u""\n',
            False,
            'from __future__ import unicode_literals\n'
            '""\n',
        ),
        # Regression: string containing newline
        ('"""with newline\n"""', True, '"""with newline\n"""'),
    ),
)
def test_unicode_literals(s, py3_plus, expected):
    ret = _fix_unicode_literals(s, py3_plus=py3_plus)
    assert ret == expected


@pytest.mark.xfail(sys.version_info >= (3,), reason='python2 "feature"')
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('5L', '5'),
        ('5l', '5'),
        ('123456789123456789123456789L', '123456789123456789123456789'),
    ),
)
def test_long_literals(s, expected):
    assert _fix_long_literals(s) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # Any number of zeros is considered a legal token
        ('0', '0'),
        ('00', '00'),
        # Don't modify non octal literals
        ('1', '1'),
        ('12345', '12345'),
        ('1.2345', '1.2345'),
    ),
)
def test_noop_octal_literals(s, expected):
    assert _fix_octal_literals(s) == expected


@pytest.mark.xfail(sys.version_info >= (3,), reason='python2 "feature"')
def test_fix_octal_literal():
    assert _fix_octal_literals('0755') == '0o755'


@pytest.mark.parametrize('s', ("b''", 'b""', 'B""', "B''", "rb''", "rb''"))
def test_is_bytestring_true(s):
    assert _is_bytestring(s) is True


@pytest.mark.parametrize('s', ('', '""', "''", 'u""', '"b"'))
def test_is_bytestring_false(s):
    assert _is_bytestring(s) is False


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            '""', (
                ('""', None),
            ),
        ),
        (
            '"%%"', (
                ('"', (None, None, None, None, '%')),
                ('"', None),
            ),
        ),
        (
            '"%s"', (
                ('"', (None, None, None, None, 's')),
                ('"', None),
            ),
        ),
        (
            '"%s two! %s"', (
                ('"', (None, None, None, None, 's')),
                (' two! ', (None, None, None, None, 's')),
                ('"', None),
            ),
        ),
        (
            '"%(hi)s"', (
                ('"', ('hi', None, None, None, 's')),
                ('"', None),
            ),
        ),
        (
            '"%()s"', (
                ('"', ('', None, None, None, 's')),
                ('"', None),
            ),
        ),
        (
            '"%#o"', (
                ('"', (None, '#', None, None, 'o')),
                ('"', None),
            ),
        ),
        (
            '"% #0-+d"', (
                ('"', (None, ' #0-+', None, None, 'd')),
                ('"', None),
            ),
        ),
        (
            '"%5d"', (
                ('"', (None, None, '5', None, 'd')),
                ('"', None),
            ),
        ),
        (
            '"%*d"', (
                ('"', (None, None, '*', None, 'd')),
                ('"', None),
            )
        ),
        (
            '"%.f"', (
                ('"', (None, None, None, '.', 'f')),
                ('"', None),
            ),
        ),
        (
            '"%.5f"', (
                ('"', (None, None, None, '.5', 'f')),
                ('"', None),
            ),
        ),
        (
            '"%.*f"', (
                ('"', (None, None, None, '.*', 'f')),
                ('"', None),
            ),
        ),
        (
            '"%ld"', (
                ('"', (None, None, None, None, 'd')),
                ('"', None),
            ),
        ),
        (
            '"%(complete)#4.4f"', (
                ('"', ('complete', '#', '4', '.4', 'f')),
                ('"', None),
            ),
        ),
    ),
)
def test_parse_percent_format(s, expected):
    assert parse_percent_format(s) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('%s', '{}'),
        ('%%%s', '%{}'),
        ('%(foo)s', '{foo}'),
        ('%2f', '{:2f}'),
        ('%r', '{!r}'),
        ('%a', '{!a}'),
    ),
)
def test_percent_to_format(s, expected):
    assert _percent_to_format(s) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('', ''),
        (' ', ' '),
        ('   ', ' '),
        ('#0- +', '#<+'),
        ('-', '<'),
    ),
)
def test_simplify_conversion_flag(s, expected):
    assert _simplify_conversion_flag(s) == expected


@pytest.mark.parametrize(
    's',
    (
        # cannot determine whether `unknown_type` is tuple or not
        '"%s" % unknown_type',
        # format of bytestring cannot be changed to `.format(...)`
        'b"%s" % (b"bytestring",)',
        # out-of-order parameter consumption
        '"%*s" % (5, "hi")', '"%.*s" % (5, "hi")',
        # potential conversion to int required
        '"%d" % (flt,)', '"%i" % (flt,)', '"%u" % (flt,)',
        # potential conversion to character required
        '"%c" % (some_string,)',
        # different output vs .format() in python 2
        '"%#o" % (123,)',
        # no format equivalent
        '"%()s" % {"": "empty"}',
        # different output in python2 / python 3
        '"%4%" % ()',
        # no equivalent in format specifier
        '"%.2r" % (1.25)', '"%.2a" % (1.25)',
        # non-string mod
        'i % 3',
        # dict format but not keyed arguments
        '"%s" % {"k": "v"}',
        # dict format must have valid identifiers
        '"%()s" % {"": "bar"}',
        '"%(1)s" % {"1": "bar"}',
        # don't trigger `SyntaxError: keyword argument repeated`
        '"%(a)s" % {"a": 1, "a": 2}',
        # don't rewrite string-joins in dict literal
        '"%(ab)s" % {"a" "b": 1}',
        # don't rewrite strangely styled things
        '"%(a)s" % {"a"  :  1}',
        # don't rewrite non-str keys
        '"%(1)s" % {1: 2, "1": 2}',
    ),
)
def test_percent_format_noop(s):
    assert _fix_percent_format(s) == s


def _has_16806_bug():
    # See https://bugs.python.org/issue16806
    return ast.parse('"""\n"""').body[0].value.col_offset == -1


@pytest.mark.xfail(not _has_16806_bug(), reason='multiline string parse bug')
def test_percent_format_noop_if_bug_16806():
    s = '"""%s\n""" % ("issue16806",)'
    assert _fix_percent_format(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # tuple
        ('"trivial" % ()', '"trivial".format()'),
        ('"%s" % ("simple",)', '"{}".format("simple")'),
        ('"%s" % ("%s" % ("nested",),)', '"{}".format("{}".format("nested"))'),
        ('"%s%% percent" % (15,)', '"{}% percent".format(15)'),
        ('"%3f" % (15,)', '"{:3f}".format(15)'),
        ('"%-5s" % ("hi",)', '"{:<5}".format("hi")'),
        ('"brace {} %s" % (1,)', '"brace {{}} {}".format(1)'),
        (
            '"%s" % (\n'
            '    "trailing comma",\n'
            ')\n',
            '"{}".format(\n'
            '    "trailing comma",\n'
            ')\n',
        ),
        # dict
        ('"%(k)s" % {"k": "v"}', '"{k}".format(k="v")'),
    ),
)
def test_percent_format(s, expected):
    assert _fix_percent_format(s) == expected


@pytest.mark.xfail
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # currently the approach does not attempt to consider joined strings
        (
            'paren_continue = (\n'
            '    "foo %s "\n'
            '    "bar %s" % (x, y)\n'
            ')\n',
            'paren_continue = (\n'
            '    "foo {} "\n'
            '    "bar {}".format(x, y)\n'
            ')\n',
        ),
        (
            'paren_string = (\n'
            '    "foo %s "\n'
            '    "bar %s"\n'
            ') % (x, y)\n',
            'paren_string = (\n'
            '    "foo {} "\n'
            '    "bar {}"\n'
            ').format(x, y)\n',
        ),
        (
            'paren_continue = (\n'
            '    "foo %(foo)s "\n'
            '    "bar %(bar)s" % {"foo": x, "bar": y}\n'
            ')\n',
            'paren_continue = (\n'
            '    "foo {foo} "\n'
            '    "bar {bar}".format(foo=x, bar=y)\n'
            ')\n',
        ),
        (
            'paren_string = (\n'
            '    "foo %(foo)s "\n'
            '    "bar %(bar)s"\n'
            ') % {"foo": x, "bar": y}\n',
            'paren_string = (\n'
            '    "foo {foo} "\n'
            '    "bar {bar}"\n'
            ').format(foo=x, bar=y)\n',
        ),
    ),
)
def test_percent_format_todo(s, expected):
    assert _fix_percent_format(s) == expected


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        'x(',

        'class C(Base):\n'
        '    def f(self):\n'
        '        super().f()\n',

        # super class doesn't match class name
        'class C(Base):\n'
        '    def f(self):\n'
        '        super(Base, self).f()\n',

        # super outside of a class (technically legal!)
        'def f(self):\n'
        '    super(C, self).f()\n',

        # super used in a comprehension
        'class C(Base):\n'
        '    def f(self):\n'
        '        return [super(C, self).f() for _ in ()]\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        return {super(C, self).f() for _ in ()}\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        return (super(C, self).f() for _ in ())\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        return {True: super(C, self).f() for _ in ()}\n',
        # nested comprehension
        'class C(Base):\n'
        '    def f(self):\n'
        '        return [\n'
        '            (\n'
        '                [_ for _ in ()],\n'
        '                super(C, self).f(),\n'
        '            )\n'
        '            for _ in ()'
        '        ]\n',
        # super in a closure
        'class C(Base):\n'
        '    def f(self):\n'
        '        def g():\n'
        '            super(C, self).f()\n'
        '        g()\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        g = lambda: super(C, self).f()\n'
        '        g()\n',
    ),
)
def test_fix_super_noop(s):
    assert _fix_super(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'class C(Base):\n'
            '    def f(self):\n'
            '        super(C, self).f()\n',
            'class C(Base):\n'
            '    def f(self):\n'
            '        super().f()\n',
        ),
        (
            'class C(Base):\n'
            '    def f(self):\n'
            '        super (C, self).f()\n',
            'class C(Base):\n'
            '    def f(self):\n'
            '        super ().f()\n',
        ),
        (
            'class Outer(object):\n'
            '    class C(Base):\n'
            '        def f(self):\n'
            '            super (C, self).f()\n',
            'class Outer(object):\n'
            '    class C(Base):\n'
            '        def f(self):\n'
            '            super ().f()\n',
        ),
        (
            'class C(Base):\n'
            '    f = lambda self: super(C, self).f()\n',
            'class C(Base):\n'
            '    f = lambda self: super().f()\n'
        ),
        (
            'class C(Base):\n'
            '    @classmethod\n'
            '    def f(cls):\n'
            '        super(C, cls).f()\n',
            'class C(Base):\n'
            '    @classmethod\n'
            '    def f(cls):\n'
            '        super().f()\n',
        ),
    ),
)
def test_fix_super(s, expected):
    assert _fix_super(s) == expected


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        'x = (',
        # does not inherit from `object`
        'class C(B): pass',
    ),
)
def test_fix_new_style_classes_noop(s):
    assert _fix_new_style_classes(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'class C(object): pass',
            'class C: pass',
        ),
        (
            'class C(\n'
            '    object,\n'
            '): pass',
            'class C: pass',
        ),
        (
            'class C(B, object): pass',
            'class C(B): pass',
        ),
        (
            'class C(B, (object)): pass',
            'class C(B): pass',
        ),
        (
            'class C(B, ( object )): pass',
            'class C(B): pass',
        ),
        (
            'class C((object)): pass',
            'class C: pass',
        ),
        (
            'class C(\n'
            '    B,\n'
            '    object,\n'
            '): pass\n',
            'class C(\n'
            '    B,\n'
            '): pass\n',
        ),
        (
            'class C(\n'
            '    B,\n'
            '    object\n'
            '): pass\n',
            'class C(\n'
            '    B\n'
            '): pass\n',
        ),
        # only legal in python2
        (
            'class C(object, B): pass',
            'class C(B): pass',
        ),
        (
            'class C((object), B): pass',
            'class C(B): pass',
        ),
        (
            'class C(( object ), B): pass',
            'class C(B): pass',
        ),
        (
            'class C(\n'
            '    object,\n'
            '    B,\n'
            '): pass',
            'class C(\n'
            '    B,\n'
            '): pass',
        ),
    ),
)
def test_fix_new_style_classes(s, expected):
    assert _fix_new_style_classes(s) == expected


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        'x = (',
        # weird attributes
        'isinstance(s, six   .    string_types)',
        # weird space at beginning of decorator
        '@  six.python_2_unicode_compatible\n'
        'class C: pass',
        # unrelated
        'from os import path',
        'from six import moves',
        # unrelated decorator
        '@mydec\n'
        'class C: pass',
        # renaming things for weird reasons
        'from six import StringIO as text_type\n'
        'isinstance(s, text_type)\n',
    )
)
def test_fix_six_noop(s):
    assert _fix_six(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'isinstance(s, six.string_types)',
            # TODO: maybe `isinstance(s, str)` (special case isinstance)
            'isinstance(s, (str,))',
        ),
        (
            'from six import string_types\n'
            'isinstance(s, string_types)\n',

            'from six import string_types\n'
            'isinstance(s, (str,))\n',
        ),
        (
            '@six.python_2_unicode_compatible\n'
            'class C: pass',

            'class C: pass',
        ),
        (
            '@six.python_2_unicode_compatible\n'
            '@other_decorator\n'
            'class C: pass',

            '@other_decorator\n'
            'class C: pass',
        ),
        (
            'from six import python_2_unicode_compatible\n'
            '@python_2_unicode_compatible\n'
            'class C: pass',

            'from six import python_2_unicode_compatible\n'
            'class C: pass',
        ),
    ),
)
def test_fix_six(s, expected):
    assert _fix_six(s) == expected


@pytest.mark.xfail(sys.version_info < (3,), reason='py3+ metaclass')
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'class C(object, metaclass=ABCMeta): pass',
            'class C(metaclass=ABCMeta): pass',
        ),
    ),
)
def test_fix_new_style_classes_py3only(s, expected):
    assert _fix_new_style_classes(s) == expected


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        '(',
        # weird syntax
        '"{}" . format(x)',
        # spans multiple lines
        '"{}".format(\n    a,\n)',
        # starargs
        '"{} {}".format(*a)', '"{foo} {bar}".format(**b)"',
        # likely makes the format longer
        '"{0} {0}".format(arg)', '"{x} {x}".format(arg)',
        '"{x.y} {x.z}".format(arg)',
        # bytestrings don't participate in `.format()` or `f''`
        # but are legal in python 2
        'b"{} {}".format(a, b)',
        # for now, too difficult to rewrite correctly
        '"{:{}}".format(x, y)',
    ),
)
def test_fix_fstrings_noop(s):
    assert _fix_fstrings(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('"{} {}".format(a, b)', 'f"{a} {b}"'),
        ('"{1} {0}".format(a, b)', 'f"{b} {a}"'),
        ('"{x.y}".format(x=z)', 'f"{z.y}"'),
        ('"{.x} {.y}".format(a, b)', 'f"{a.x} {b.y}"'),
        ('"{} {}".format(a.b, c.d)', 'f"{a.b} {c.d}"'),
        ('"hello {}!".format(name)', 'f"hello {name}!"'),
        ('"{}{{}}{}".format(escaped, y)', 'f"{escaped}{{}}{y}"'),

        # TODO: poor man's f-strings?
        # '"{foo}".format(**locals())'
    ),
)
def test_fix_fstrings(s, expected):
    assert _fix_fstrings(s) == expected


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


def test_main_keeps_line_endings(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary(b'x = set((1, 2, 3))\r\n')
    assert main((f.strpath,)) == 1
    assert f.read_binary() == b'x = {1, 2, 3}\r\n'


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


def test_py3_plus_argument_unicode_literals(tmpdir):
    f = tmpdir.join('f.py')
    f.write('u""')
    assert main((f.strpath,)) == 0
    assert f.read() == 'u""'
    assert main((f.strpath, '--py3-plus')) == 1
    assert f.read() == '""'


def test_py3_plus_super(tmpdir):
    f = tmpdir.join('f.py')
    f.write(
        'class C(Base):\n'
        '    def f(self):\n'
        '        super(C, self).f()\n',
    )
    assert main((f.strpath,)) == 0
    assert f.read() == (
        'class C(Base):\n'
        '    def f(self):\n'
        '        super(C, self).f()\n'
    )
    assert main((f.strpath, '--py3-plus')) == 1
    assert f.read() == (
        'class C(Base):\n'
        '    def f(self):\n'
        '        super().f()\n'
    )


def test_py3_plus_new_style_classes(tmpdir):
    f = tmpdir.join('f.py')
    f.write('class C(object): pass\n')
    assert main((f.strpath,)) == 0
    assert f.read() == 'class C(object): pass\n'
    assert main((f.strpath, '--py3-plus')) == 1
    assert f.read() == 'class C: pass\n'


def test_py36_plus_fstrings(tmpdir):
    f = tmpdir.join('f.py')
    f.write('"{} {}".format(hello, world)')
    assert main((f.strpath,)) == 0
    assert f.read() == '"{} {}".format(hello, world)'
    assert main((f.strpath, '--py36-plus')) == 1
    assert f.read() == 'f"{hello} {world}"'
