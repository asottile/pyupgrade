from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'class ExampleTests:\n'
            '    def test_something(self):\n'
            '        self.assertEqual(1, 1)\n',
            id='not a deprecated alias',
        ),
        'unittest.makeSuite(Tests, "arg")',
        'unittest.makeSuite(Tests, prefix="arg")',
    ),
)
def test_fix_unittest_aliases_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


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
def test_fix_unittest_aliases(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'unittest.findTestCases(MyTests)',
            'unittest.defaultTestLoader.loadTestsFromModule(MyTests)',
        ),
        (
            'unittest.makeSuite(MyTests)',
            'unittest.defaultTestLoader.loadTestsFromTestCase(MyTests)',
        ),
        (
            'unittest.getTestCaseNames(MyTests)',
            'unittest.defaultTestLoader.getTestCaseNames(MyTests)',
        ),
    ),
)
def test_fix_unittest_aliases_py311(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 11)))
    assert ret == expected
