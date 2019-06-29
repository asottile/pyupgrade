# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys

import pytest

from pyupgrade import _fix_py3_plus


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
    assert _fix_py3_plus(s) == s


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
    ),
)
def test_fix_classes(s, expected):
    assert _fix_py3_plus(s) == expected


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
def test_fix_classes_py3only(s, expected):
    assert _fix_py3_plus(s) == expected
