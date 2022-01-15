from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            '"{x}".format(**locals())',
            (3,),
            id='not 3.6+',
        ),
        pytest.param(
            '"{x} {y}".format(x, **locals())',
            (3, 6),
            id='mixed locals() and params',
        ),
    ),
)
def test_fix_format_locals_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            '"{x}".format(**locals())',
            'f"{x}"',
            id='normal case',
        ),
        pytest.param(
            '"{x}" "{y}".format(**locals())',
            'f"{x}" f"{y}"',
            id='joined strings',
        ),
        pytest.param(
            '(\n'
            '    "{x}"\n'
            '    "{y}"\n'
            ').format(**locals())\n',
            '(\n'
            '    f"{x}"\n'
            '    f"{y}"\n'
            ')\n',
            id='joined strings with parens',
        ),
    ),
)
def test_fix_format_locals(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == expected
