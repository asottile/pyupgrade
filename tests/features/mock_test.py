from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import mock.mock\n'
            '\n'
            'mock.mock.patch("func1")\n'
            'mock.patch("func2")\n',
            'from unittest import mock\n'
            '\n'
            'mock.patch("func1")\n'
            'mock.patch("func2")\n',
            id='double mock absolute import func',
        ),
        pytest.param(
            'import mock.mock\n'
            '\n'
            'mock.mock.patch.object(Foo, "func1")\n'
            'mock.patch.object(Foo, "func2")\n',
            'from unittest import mock\n'
            '\n'
            'mock.patch.object(Foo, "func1")\n'
            'mock.patch.object(Foo, "func2")\n',
            id='double mock absolute import func attr',
        ),
    ),
)
def test_fix_mock(s, expected):
    assert _fix_plugins(s, settings=Settings()) == expected
