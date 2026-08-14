from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_noop_before_315():
    s = '''argparse.ArgumentParser(suggest_on_error=True)'''
    assert _fix_plugins(s, settings=Settings(min_version=(3, 14))) == s


@pytest.mark.parametrize(
    's',
    (
        # already removed
        'argparse.ArgumentParser()',
        # explicitly off
        'argparse.ArgumentParser(suggest_on_error=False)',
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 15))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'argparse.ArgumentParser(suggest_on_error=True)',
            'argparse.ArgumentParser()',
            id='simple case',
        ),
        pytest.param(
            'from argparse import ArgumentParser\n'
            'ArgumentParser(suggest_on_error=True)',

            'from argparse import ArgumentParser\n'
            'ArgumentParser()',
            id='from import',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert ret == expected
