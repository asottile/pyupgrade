from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        '(',
        # invalid format strings
        "'{'.format(a)", "'}'.format(a)",
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
        '"{a[b]}".format(a=a)',
        '"{a.a[b]}".format(a=a)',
        # not enough placeholders / placeholders missing
        '"{}{}".format(a)', '"{a}{b}".format(a=a)',
        # backslashes and quotes cannot nest
        r'''"{}".format(a['\\'])''',
        '"{}".format(a["b"])',
        "'{}'.format(a['b'])",
        # await only becomes keyword in Python 3.7+
        "async def c(): return '{}'.format(await 3)",
        "async def c(): return '{}'.format(1 + await 3)",
    ),
)
def test_fix_fstrings_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('"{} {}".format(a, b)', 'f"{a} {b}"'),
        ('"{1} {0}".format(a, b)', 'f"{b} {a}"'),
        ('"{x.y}".format(x=z)', 'f"{z.y}"'),
        ('"{.x} {.y}".format(a, b)', 'f"{a.x} {b.y}"'),
        ('"{} {}".format(a.b, c.d)', 'f"{a.b} {c.d}"'),
        ('"{}".format(a())', 'f"{a()}"'),
        ('"{}".format(a.b())', 'f"{a.b()}"'),
        ('"{}".format(a.b().c())', 'f"{a.b().c()}"'),
        ('"hello {}!".format(name)', 'f"hello {name}!"'),
        ('"{}{{}}{}".format(escaped, y)', 'f"{escaped}{{}}{y}"'),
        ('"{}{b}{}".format(a, c, b=b)', 'f"{a}{b}{c}"'),
        ('"{}".format(0x0)', 'f"{0x0}"'),
        pytest.param(
            r'"\N{snowman} {}".format(a)',
            r'f"\N{snowman} {a}"',
            id='named escape sequences',
        ),
        pytest.param(
            'u"foo{}".format(1)',
            'f"foo{1}"',
            id='u-prefixed format',
        ),
    ),
)
def test_fix_fstrings(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == expected


def test_fix_fstrings_await_py37():
    s = "async def c(): return '{}'.format(await 1+foo())"
    expected = "async def c(): return f'{await 1+foo()}'"
    assert _fix_plugins(s, settings=Settings(min_version=(3, 7))) == expected
