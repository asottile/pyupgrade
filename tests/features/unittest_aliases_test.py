from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertEqual(1, 1)\n',
            id='not a deprecated alias',
        ),
        pytest.param(
            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertNotEquals(1, 2)\n',
            id='not python 3+',
        ),
    ),
)
def test_fix_unittest_aliases_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(2, 7))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertEquals(1, 1)\n',

            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertEqual(1, 1)\n',
        ),
    ),
)
def test_fix_unittest_aliases_py27(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(2, 7)))
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertNotEquals(1, 2)\n',

            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertNotEqual(1, 2)\n',
        ),
    ),
)
def test_fix_unittest_aliases_py3(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3,)))
    assert ret == expected
