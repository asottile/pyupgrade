from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # Don't touch empty set literals
        'set()',
        # Don't touch weird looking function calls -- use autopep8 or such
        # first
        'set ((1, 2))',
    ),
)
def test_fix_sets_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        # Take a set literal with an empty tuple / list and remove the arg
        ('set(())', 'set()'),
        ('set([])', 'set()'),
        pytest.param('set (())', 'set ()', id='empty, weird ws'),
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
        (
            'set(\n'
            '    [\n'
            '        99, 100,\n'
            '    ],\n'
            ')\n',
            '{\n'
            '        99, 100,\n'
            '}\n',
        ),
        pytest.param('set((\n))', 'set()', id='empty literal with newline'),
        pytest.param(
            'set((f"{x}(",))',
            '{f"{x}("}',
            id='3.12 fstring containing open brace',
        ),
        pytest.param(
            'set((f"{x})",))',
            '{f"{x})"}',
            id='3.12 fstring containing close brace',
        ),
    ),
)
def test_sets(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
