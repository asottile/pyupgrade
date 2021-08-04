import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'foo(*[i for i in bar])\n',
            (2, 7),
            id='Not Python3+',
        ),
        pytest.param(
            '2*3',
            (3,),
            id='Multiplication star',
        ),
        pytest.param(
            '2**3',
            (3,),
            id='Power star',
        ),
        pytest.param(
            'foo([i for i in bar])',
            (3,),
            id='List comp, no star',
        ),
        pytest.param(
            'foo(*bar)',
            (3,),
            id='Starred, no list comp',
        ),
        pytest.param(
            'foo(*[x async for x in bar])',
            (3,),
            id='async listcomp',
        ),
    ),
)
def test_fix_unpack_argument_list_comp_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'foo(*[i for i in bar])\n',

            'foo(*(i for i in bar))\n',

            id='Starred list comprehension',
        ),
        pytest.param(
            'foo(\n'
            '    *\n'
            '        [i for i in bar]\n'
            '    )\n',

            'foo(\n'
            '    *\n'
            '        (i for i in bar)\n'
            '    )\n',

            id='Multiline starred list comprehension',
        ),
        pytest.param(
            'foo(*[i for i in bar], qux, quox=None)\n',

            'foo(*(i for i in bar), qux, quox=None)\n',

            id='Single line, including other args',
        ),
    ),
)
def test_fix_unpack_argument_list_comp(s, expected):
    ret = _fix_plugins(s, settings=Settings((3,)))
    assert ret == expected
