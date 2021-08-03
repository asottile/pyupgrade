import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            '{**a, **b}\n',
            (3, 8),
            id='<3.9',
        ),
        pytest.param(
            '{"a": 0}\n',
            (3, 9),
            id='Dict without merge',
        ),
        pytest.param(
            'x = {**a}\n',
            (3, 9),
            id='Merge of only one dict',
        ),
    ),
)
def test_fix_pep584_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'x = {**a, **b}\n',

            'x = a | b\n',

            id='Simple dict rewrite',
        ),
        pytest.param(
            'x = {**{**a, **b}, **c}\n',

            'x = a | b | c\n',

            id='Nested merge of dicts',
        ),
        pytest.param(
            'x = {**a, **b,}\n',

            'x = a | b\n',

            id='Trailing comma',
        ),
        pytest.param(
            'x = {\n'
            '    **a,  # foo\n'
            '    **b  # bar\n'
            '}\n',

            'x = (\n'
            '    a |  # foo\n'
            '    b  # bar\n'
            ')\n',

            id='Multiple lines with comment',
        ),
        pytest.param(
            'x = {\n'
            '    **a,\n'
            '    **b\n'
            '}\n',

            'x = (\n'
            '    a |\n'
            '    b\n'
            ')\n',

            id='Multiple lines',
        ),
        pytest.param(
            'x = {\n'
            '    **a,\n'
            '    **b,\n'
            '}\n',

            'x = (\n'
            '    a |\n'
            '    b\n'
            ')\n',

            id='Multiple lines, trailing comma',
        ),
        pytest.param(
            'x = {\n'
            '    **{a: a for a  in range(3)},\n'
            '    **b,\n'
            '}\n',

            'x = (\n'
            '    {a: a for a  in range(3)} |\n'
            '    b\n'
            ')\n',

            id='Dict comprehension within merge of dicts',
        ),
        pytest.param(
            'x = {\n'
            '    **{a: b for a, b in zip(range(3), range(3))},\n'
            '    **b,\n'
            '}\n',

            'x = (\n'
            '    {a: b for a, b in zip(range(3), range(3))} |\n'
            '    b\n'
            ')\n',

            id='Dict with comma inside it',
        ),
    ),
)
def test_fix_pep584(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 9))) == expected
