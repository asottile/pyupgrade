import sys

import pytest

from pyupgrade import _fix_py3_plus


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'from typing import List\n'
            'x: List[int]\n',
            (3, 8),
            id='not python 3.9+',
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
    assert _fix_py3_plus(s, version) == s


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
    ),
)
def test_fix_generic_types(s, expected):
    assert _fix_py3_plus(s, (3, 9)) == expected


@pytest.mark.xfail(sys.version_info < (3, 7), reason='py37+ feature')
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'from __future__ import annotations\n'
            'from typing import List\n'
            'x: List[int]\n',

            'from __future__ import annotations\n'
            'from typing import List\n'
            'x: list[int]\n',
        ),
    ),
)
def test_fix_generic_types_future_annotations(s, expected):
    assert _fix_py3_plus(s, (3,)) == expected
