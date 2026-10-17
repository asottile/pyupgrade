from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        'x = (',
        # does not inherit from `object`
        'class C(B): pass',
        'type("A", (B,), {})',
        'type("A", (object, B), {})',
        'type("A", (B, object), {})',
        'type("A", object, {})',
        'not_type("A", (object,), {})',
    ),
)
def test_fix_classes_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


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
        (
            'class C(\n'
            '    object,  # comment!\n'
            '    B,\n'
            '): pass',
            'class C(\n'
            '    B,\n'
            '): pass',
        ),
        (
            'class C(object, metaclass=ABCMeta): pass',
            'class C(metaclass=ABCMeta): pass',
        ),
        (
            'type("A", (object,), {})',
            'type("A", (), {})',
        ),
        (
            'type("A", (object, ), {})',
            'type("A", (), {})',
        ),
        (
            'type("A", ((object,)), {})',
            'type("A", (), {})',
        ),
        (
            'type("A", (( object , )), {})',
            'type("A", (), {})',
        ),
        (
            'type("A", (\n'
            '    object,\n'
            '), {})',
            'type("A", (), {})',
        ),
        (
            'type("A", (\n'
            '    object,  # comment!\n'
            '), {})',
            'type("A", (), {})',
        ),
    ),
)
def test_fix_classes(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
