import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'import contextlib, mock, sys\n',
            id='does not rewrite multiple imports',
        ),
        pytest.param(
            'from .mock import patch\n',
            id='leave relative imports alone',
        ),
    ),
)
def test_mock_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == s


def test_mock_noop_keep_mock():
    """This would've been rewritten if keep_mock were False"""
    s = (
        'from mock import patch\n'
        '\n'
        'patch("func")'
    )
    settings = Settings(min_version=(3,), keep_mock=True)
    assert _fix_plugins(s, settings=settings) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from mock import patch\n'
            '\n'
            'patch("func")',
            'from unittest.mock import patch\n'
            '\n'
            'patch("func")',
            id='relative import func',
        ),
        pytest.param(
            'import mock\n'
            '\n'
            'mock.patch("func")\n',
            'from unittest import mock\n'
            '\n'
            'mock.patch("func")\n',
            id='absolute import func',
        ),
        pytest.param(
            'from mock.mock import patch\n'
            '\n'
            'patch("func")\n',
            'from unittest.mock import patch\n'
            '\n'
            'patch("func")\n',
            id='double mock relative import func',
        ),
        pytest.param(
            'import mock.mock\n'
            '\n'
            'mock.mock.patch("func1")\n'
            'mock.patch("func2")\n',
            'from unittest import mock\n'
            '\n'
            'mock.patch("func1")\n'
            'mock.patch("func2")\n',
            id='double mock absolute import func',
        ),

        pytest.param(
            'from mock import mock\n',
            'from unittest import mock\n',
            id='relative import mock',
        ),        
        pytest.param(
            'from mock import mock, patch\n',
            'from unittest import mock\n'
            'from unittest.mock import  patch\n',
            id='relative import mock and func',
        ),        
        pytest.param(
            'from mock import patch, mock\n',
            'from unittest import mock\n'
            'from unittest.mock import patch\n',
            id='relative import func and mock',
        ),        
        pytest.param(
            'from mock import (\n'
            '  mock as mock2, patch\n'
            ')\n',
            'from unittest import mock as mock2\n'
            'from unittest.mock import (\n'
            '   patch\n'
            ')\n',
            id='relative import func and mock',
        ),               

        pytest.param(
            'from mock import patch\n'
            '\n'
            'patch.object(Foo, "func")\n',
            'from unittest.mock import patch\n'
            '\n'
            'patch.object(Foo, "func")\n',
            id='relative import func attr',
        ),
        pytest.param(
            'import mock\n'
            '\n'
            'mock.patch.object(Foo, "func")\n',
            'from unittest import mock\n'
            '\n'
            'mock.patch.object(Foo, "func")\n',
            id='absolute import func attr',
        ),
        pytest.param(
            'from mock.mock import patch\n'
            '\n'
            'patch.object(Foo, "func")\n',
            'from unittest.mock import patch\n'
            '\n'
            'patch.object(Foo, "func")\n',
            id='double mock relative import func attr',
        ),
        pytest.param(
            'import mock.mock\n'
            '\n'
            'mock.mock.patch.object(Foo, "func1")\n'
            'mock.patch.object(Foo, "func2")\n',
            'from unittest import mock\n'
            '\n'
            'mock.patch.object(Foo, "func1")\n'
            'mock.patch.object(Foo, "func2")\n',
            id='double mock absolute import func attr',
        ),

        pytest.param(
            'from mock import patch as patch2\n',
            'from unittest.mock import patch as patch2\n',
            id='relative import with as',
        ),
        pytest.param(
            'import mock as mock2\n',
            'from unittest import mock as mock2\n',
            id='absolute import with as',
        ),
        pytest.param(
            'from mock.mock import patch as patch2\n',
            'from unittest.mock import patch as patch2\n',
            id='double mock relative import with as',
        ),
        pytest.param(
            'import mock.mock as mock2\n',
            'from unittest import mock as mock2\n',
            id='double mock absolute import with as',
        ),

        pytest.param(
            'from mock import *\n',
            'from unittest.mock import *\n',
            id='relative import with star',
        ),
        pytest.param(
            'from mock.mock import *\n',
            'from unittest.mock import *\n',
            id='double mock relative import with star',
        ),
    ),
)
def test_fix_mock(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == expected
