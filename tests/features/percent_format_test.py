from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins
from pyupgrade._plugins.percent_format import _parse_percent_format
from pyupgrade._plugins.percent_format import _percent_to_format
from pyupgrade._plugins.percent_format import _simplify_conversion_flag


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
            ),
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
    assert _parse_percent_format(s) == expected


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
        pytest.param('"%8s" % (None,)', id='unsafe width-string conversion'),
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
        # don't rewrite keyword keys
        '"%(and)s" % {"and": 2}',
        # invalid string formats
        '"%" % {}', '"%(hi)" % {}', '"%2" % {}',
    ),
)
def test_percent_format_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # tuple
        ('"trivial" % ()', '"trivial".format()'),
        ('"%s" % ("simple",)', '"{}".format("simple")'),
        ('"%s" % ("%s" % ("nested",),)', '"{}".format("{}".format("nested"))'),
        ('"%s%% percent" % (15,)', '"{}% percent".format(15)'),
        ('"%3f" % (15,)', '"{:3f}".format(15)'),
        ('"%-5f" % (5,)', '"{:<5f}".format(5)'),
        ('"%9f" % (5,)', '"{:9f}".format(5)'),
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
        ('"%(to_list)s" % {"to_list": []}', '"{to_list}".format(to_list=[])'),
        # \N escapes
        (
            r'"%s \N{snowman}" % (a,)',
            r'"{} \N{snowman}".format(a)',
        ),
        (
            r'"%(foo)s \N{snowman}" % {"foo": 1}',
            r'"{foo} \N{snowman}".format(foo=1)',
        ),
    ),
)
def test_percent_format(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected


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
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
