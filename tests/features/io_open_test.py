import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        # when using open without referencing io we don't need to rewrite
        'from io import open\n\n'
        'with open("f.txt") as f:\n'
        '     print(f.read())\n',
    ),
)
def test_fix_io_open_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'import io\n\n'
            'with io.open("f.txt", mode="r", buffering=-1, **kwargs) as f:\n'
            '   print(f.read())\n',

            'import io\n\n'
            'with open("f.txt", mode="r", buffering=-1, **kwargs) as f:\n'
            '   print(f.read())\n',
        ),
    ),
)
def test_fix_io_open(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3,)))
    assert ret == expected
