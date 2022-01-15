from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # Don't touch irrelevant code
        'x = 5',
        'dict()',
        # Don't touch syntax errors
        '(',
        # Don't touch strange looking calls
        'dict ((a, b) for a, b in y)',
        # Don't rewrite kwargd dicts
        'dict(((a, b) for a, b in y), x=1)',
        'dict(((a, b) for a, b in y), **kwargs)',
    ),
)
def test_fix_dict_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
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
        ),
    ),
)
def test_dictcomps(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
