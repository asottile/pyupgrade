from __future__ import annotations

import sys

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


def test_noop_before_315():
    s = '''\
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import LiteralString
'''
    assert _fix_plugins(s, settings=Settings(min_version=(3, 14))) == s


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'from typing import TYPE_CHECKING\n'
            'if TYPE_CHECKING:\n'
            '    from typing import Protocol\n'
            'else:\n'
            '    Protocol = object\n',
            id='with else',
        ),
        pytest.param(
            'from typing import TYPE_CHECKING\n'
            'if TYPE_CHECKING:\n'
            '    from typing import LiteralString\n'
            '    class SomeClass: pass\n',
            id='has other junk',
        ),
        pytest.param(
            'from typing import TYPE_CHECKING\n'
            'def f():\n'
            '    if TYPE_CHECKING:\n'
            '        from typing import LiteralString\n',
            id='not at module scope',
        ),
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 15))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from typing import TYPE_CHECKING\n'
            'if TYPE_CHECKING:\n'
            '    from typing import LiteralString\n',

            'from typing import TYPE_CHECKING\n'
            'lazy from typing import LiteralString\n',

            id='simple case',
        ),
        pytest.param(
            'from typing_extensions import TYPE_CHECKING\n'
            'if TYPE_CHECKING:\n'
            '    from typing import LiteralString\n',

            'from typing import TYPE_CHECKING\n'
            'lazy from typing import LiteralString\n',

            id='via typing_extensions',
        ),
        pytest.param(
            'from typing import TYPE_CHECKING\n'
            'if TYPE_CHECKING:\n'
            '    import typing as T\n',

            'from typing import TYPE_CHECKING\n'
            'lazy import typing as T\n',

            id='import-import',
        ),
        pytest.param(
            'if False:\n'
            '    from typing import LiteralString\n',

            'lazy from typing import LiteralString\n',

            id='old-style type checking block',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert ret == expected


@pytest.mark.skipif(sys.version_info < (3, 15), reason='py315+')
def test_already_lazy():  # pragma: >=3.15 cover
    s = '''\
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    lazy from typing import LiteralString
'''
    expected = '''\
from typing import TYPE_CHECKING
lazy from typing import LiteralString
'''
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert ret == expected
