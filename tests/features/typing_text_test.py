from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'class Text: ...\n'
            'text = Text()\n',
            id='not a type annotation',
        ),
    ),
)
def test_fix_typing_text_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from typing import Text\n'
            'x: Text\n',

            'from typing import Text\n'
            'x: str\n',

            id='from import of Text',
        ),
        pytest.param(
            'import typing\n'
            'x: typing.Text\n',

            'import typing\n'
            'x: str\n',

            id='import of typing + typing.Text',
        ),
        pytest.param(
            'from typing import Text\n'
            'SomeAlias = Text\n',
            'from typing import Text\n'
            'SomeAlias = str\n',
            id='not in a type annotation context',
        ),
    ),
)
def test_fix_typing_text(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
