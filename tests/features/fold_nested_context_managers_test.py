from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'with foo:\n'
            "    print('something')\n"
            '\n',
            (3, 10),
            id='simple with expression',
        ),
        pytest.param(
            'with foo as bar:\n'
            "    print('something')\n"
            '\n',
            (3, 10),
            id='simple with expression and captured name',
        ),
        pytest.param(
            'with (foo as thing1, bar as thing2):\n'
            "    print('something')\n"
            '\n',
            (3, 10),
            id='simple with expression and captured names',
        ),
        pytest.param(
            'with (foo as _, bar as _):\n'
            "    print('something')\n"
            '\n',
            (3, 9),
            id='nested with expression with empty name capture workaround',
        ),
    ),
)
def test_fold_nested_context_managers_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected', 'version'),
    (
        pytest.param(
            'with foo:\n'
            '    with bar:\n'
            "        print('something')\n"
            "        print('another')\n"
            '\n',
            'with (foo, bar):\n'
            "    print('something')\n"
            "    print('another')\n"
            '\n',
            (3, 10),
            id='nested with expression',
        ),
        pytest.param(
            'if value:\n'
            '    with foo:\n'
            '        with bar:\n'
            "            print('something')\n"
            "            print('another')\n"
            '\n',
            'if value:\n'
            '    with (foo, bar):\n'
            "        print('something')\n"
            "        print('another')\n"
            '\n',
            (3, 10),
            id='nested with expression inside of an if',
        ),
        pytest.param(
            'with foo as thing1:\n'
            '    with bar as thing2:\n'
            "        print('something')\n"
            "        print('another')\n"
            '\n',
            'with (foo as thing1, bar as thing2):\n'
            "    print('something')\n"
            "    print('another')\n"
            '\n',
            (3, 10),
            id='nested with expression with named capture',
        ),
        pytest.param(
            'with (foo as _, bar as _):\n'
            "    print('something')\n"
            '\n',
            'with (foo, bar):\n'
            "    print('something')\n"
            '\n',
            (3, 10),
            id='nested with expression with unnecessary empty name capture workaround',  # noqa: E501
        ),
        pytest.param(
            'with (foo as _, bar as thing2):\n'
            "    print('something')\n"
            '\n',
            'with (foo, bar as thing2):\n'
            "    print('something')\n"
            '\n',
            (3, 10),
            id='nested with expression with one unnecessary empty name capture workaround',  # noqa: E501
        ),
    ),
)
def test_fold_nested_context_managers(s, expected, version):
    ret = _fix_plugins(s, settings=Settings(min_version=version))
    assert ret == expected
