from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'x = lambda foo: None',
            (3, 9),
            id='lambdas do not have type annotations',
        ),
        pytest.param(
            'from typing import List\n'
            'x: List[int]\n',
            (3, 8),
            id='not python 3.9+',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from typing import List\n'
            'SomeAlias = List[int]\n',
            (3, 8),
            id='not in a type annotation context',
        ),
        pytest.param(
            'from typing import Union\n'
            'x: Union[int, str]\n',
            (3, 9),
            id='not a PEP 585 type',
        ),
    ),
)
def test_fix_generic_types_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


def test_noop_keep_runtime_typing():
    s = '''\
from __future__ import annotations
from typing import List
def f(x: List[str]) -> None: ...
'''
    assert _fix_plugins(s, settings=Settings(keep_runtime_typing=True)) == s


def test_keep_runtime_typing_ignored_in_py39():
    s = '''\
from __future__ import annotations
from typing import List
def f(x: List[str]) -> None: ...
'''
    expected = '''\
from __future__ import annotations
from typing import List
def f(x: list[str]) -> None: ...
'''
    settings = Settings(min_version=(3, 9), keep_runtime_typing=True)
    assert _fix_plugins(s, settings=settings) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from typing import List\n'
            'x: List[int]\n',

            'from typing import List\n'
            'x: list[int]\n',

            id='from import of List',
        ),
        pytest.param(
            'import typing\n'
            'x: typing.List[int]\n',

            'import typing\n'
            'x: list[int]\n',

            id='import of typing + typing.List',
        ),
        pytest.param(
            'from typing import List\n'
            'SomeAlias = List[int]\n',
            'from typing import List\n'
            'SomeAlias = list[int]\n',
            id='not in a type annotation context',
        ),
    ),
)
def test_fix_generic_types(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 9)))
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from __future__ import annotations\n'
            'from typing import List\n'
            'x: List[int]\n',

            'from __future__ import annotations\n'
            'from typing import List\n'
            'x: list[int]\n',

            id='variable annotations',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from typing import List\n'
            'def f(x: List[int]) -> None: ...\n',

            'from __future__ import annotations\n'
            'from typing import List\n'
            'def f(x: list[int]) -> None: ...\n',

            id='argument annotations',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'from typing import List\n'
            'def f() -> List[int]: ...\n',

            'from __future__ import annotations\n'
            'from typing import List\n'
            'def f() -> list[int]: ...\n',

            id='return annotations',
        ),
    ),
)
def test_fix_generic_types_future_annotations(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
