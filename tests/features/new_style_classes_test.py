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
    ),
)
def test_fix_classes(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'A = type("A", (), {})\n',
            id='already empty bases',
        ),
        pytest.param(
            'A = type("A", (B,), {})\n',
            id='non-object base',
        ),
        pytest.param(
            'type("A", (object,))\n',
            id='type call with only 2 args',
        ),
        pytest.param(
            'type(x)\n',
            id='type call with 1 arg',
        ),
        pytest.param(
            'type("A", (object,), {}, extra)\n',
            id='type call with 4 args',
        ),
        pytest.param(
            'type("A", (object,), {}, key=val)\n',
            id='type call with keyword args',
        ),
        pytest.param(
            'type("A", object, {})\n',
            id='bases not a tuple',
        ),
    ),
)
def test_fix_type_call_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'A = type("A", (object,), {})\n',
            'A = type("A", (), {})\n',
            id='single object base',
        ),
        pytest.param(
            'A = type("A", (object, ), {})\n',
            'A = type("A", (), {})\n',
            id='single object base with trailing space',
        ),
        pytest.param(
            'A = type("A", (Foo, object), {})\n',
            'A = type("A", (Foo,), {})\n',
            id='object with other base',
        ),
        pytest.param(
            'A = type("A", (object, Foo), {})\n',
            'A = type("A", (Foo,), {})\n',
            id='object before other base',
        ),
        pytest.param(
            'A = type("A", (Foo, object, Bar), {})\n',
            'A = type("A", (Foo, Bar), {})\n',
            id='object between two bases',
        ),
    ),
)
def test_fix_type_call(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
