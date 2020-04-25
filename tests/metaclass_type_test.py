import pytest

from pyupgrade import _fix_py3_plus


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'x = type\n'
            '__metaclass__ = x\n',
            id='not rewriting "type" rename',
        ),
        pytest.param(
            'def foo():\n'
            '    __metaclass__ = type\n',
            id='not rewriting function scope',
        ),
        pytest.param(
            'class Foo:\n'
            '    __metaclass__ = type\n',
            id='not rewriting class scope',
        ),
        pytest.param(
            '__metaclass__, __meta_metaclass__ = type, None\n',
            id='not rewriting multiple assignment',
        ),
    ),
)
def test_metaclass_type_assignment_noop(s):
    assert _fix_py3_plus(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            '__metaclass__ = type',
            '',
            id='module-scope assignment',
        ),
        pytest.param(
            '__metaclass__  =   type',
            '',
            id='module-scope assignment with extra whitespace',
        ),
        pytest.param(
            '__metaclass__ = (\n'
            '   type\n'
            ')\n',
            '',
            id='module-scope assignment across newline',
        ),
    ),
)
def test_fix_metaclass_type_assignment(s, expected):
    assert _fix_py3_plus(s) == expected
