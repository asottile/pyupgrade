import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'foo, bar, baz = [fn(x) for x in items]\n',
            (2, 7),
            id='not python 3+',
        ),
        pytest.param(
            'foo = [fn(x) for x in items]',
            (3,),
            id='assignment to single variable',
        ),
        pytest.param(
            'x, = [await foo for foo in bar]',
            (3,),
            id='async comprehension',
        ),
    ),
)
def test_fix_typing_text_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'foo, bar, baz = [fn(x) for x in items]\n',

            'foo, bar, baz = (fn(x) for x in items)\n',

            id='single-line assignment',
        ),
        pytest.param(
            'foo, bar, baz = [[i for i in fn(x)] for x in items]\n',

            'foo, bar, baz = ([i for i in fn(x)] for x in items)\n',

            id='nested list comprehension',
        ),
        pytest.param(
            'foo, bar, baz = [\n'
            '    fn(x)\n'
            '    for x in items\n'
            ']\n',

            'foo, bar, baz = (\n'
            '    fn(x)\n'
            '    for x in items\n'
            ')\n',

            id='multi-line assignment',
        ),
    ),
)
def test_fix_typing_text(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3,)))
    assert ret == expected
