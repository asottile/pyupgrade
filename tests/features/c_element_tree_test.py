from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'import xml.etree.cElementTree as ET',
            (2, 7),
            id='not Python3+',
        ),
        pytest.param(
            'import contextlib, xml.etree.ElementTree as ET\n',
            (3,),
            id='does not rewrite multiple imports',
        ),
        pytest.param(
            'import xml.etree.cElementTree',
            (3,),
            id='import without alias',
        ),
    ),
)
def test_c_element_tree_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import xml.etree.cElementTree as ET',
            'import xml.etree.ElementTree as ET',
            id='import with alias',
        ),
    ),
)
def test_fix_c_element_tree(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3,))) == expected
