from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'from collections import defaultdict as dd\n\n'
            'dd(lambda: set())\n',
            id='not following as imports',
        ),
        pytest.param(
            'from collections2 import defaultdict\n\n'
            'dd(lambda: dict())\n',
            id='not following unknown import',
        ),
        pytest.param(
            'from .collections import defaultdict\n'
            'defaultdict(lambda: list())\n',
            id='relative imports',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: {1}))\n',
            id='non empty set',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: [1]))\n'
            'defaultdict(lambda: list([1])))\n',
            id='non empty list',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: {1: 2})\n',
            id='non empty dict, literal',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: dict([(1,2),])))\n',
            id='non empty dict, call with args',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: dict(a=[1]))\n',
            id='non empty dict, call with kwargs',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: (1,))\n',
            id='non empty tuple, literal',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: tuple([1]))\n',
            id='non empty tuple, calls with arg',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: "AAA")\n'
            'defaultdict(lambda: \'BBB\')\n',
            id='non empty string',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: 10)\n'
            'defaultdict(lambda: -2)\n',
            id='non zero integer',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: 0.2)\n'
            'defaultdict(lambda: 0.00000001)\n'
            'defaultdict(lambda: -2.3)\n',
            id='non zero float',
        ),
        pytest.param(
            'import collections\n'
            'collections.defaultdict(lambda: None)\n',
            id='lambda: None is not equivalent to defaultdict()',
        ),
    ),
)
def test_fix_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: set())\n',
            'from collections import defaultdict\n\n'
            'defaultdict(set)\n',
            id='call with attr, set()',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: list())\n',
            'from collections import defaultdict\n\n'
            'defaultdict(list)\n',
            id='call with attr, list()',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: dict())\n',
            'from collections import defaultdict\n\n'
            'defaultdict(dict)\n',
            id='call with attr, dict()',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: tuple())\n',
            'from collections import defaultdict\n\n'
            'defaultdict(tuple)\n',
            id='call with attr, tuple()',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: [])\n',
            'from collections import defaultdict\n\n'
            'defaultdict(list)\n',
            id='call with attr, []',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: {})\n',
            'from collections import defaultdict\n\n'
            'defaultdict(dict)\n',
            id='call with attr, {}',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: ())\n',
            'from collections import defaultdict\n\n'
            'defaultdict(tuple)\n',
            id='call with attr, ()',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: "")\n',
            'from collections import defaultdict\n\n'
            'defaultdict(str)\n',
            id='call with attr, empty string (double quote)',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: \'\')\n',
            'from collections import defaultdict\n\n'
            'defaultdict(str)\n',
            id='call with attr, empty string (single quote)',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: 0)\n',
            'from collections import defaultdict\n\n'
            'defaultdict(int)\n',
            id='call with attr, int',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: 0.0)\n',
            'from collections import defaultdict\n\n'
            'defaultdict(float)\n',
            id='call with attr, float',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: 0.0000)\n',
            'from collections import defaultdict\n\n'
            'defaultdict(float)\n',
            id='call with attr, long float',
        ),
        pytest.param(
            'from collections import defaultdict\n\n'
            'defaultdict(lambda: [], {1: []})\n',
            'from collections import defaultdict\n\n'
            'defaultdict(list, {1: []})\n',
            id='defauldict with kwargs',
        ),
        pytest.param(
            'import collections\n\n'
            'collections.defaultdict(lambda: set())\n'
            'collections.defaultdict(lambda: list())\n'
            'collections.defaultdict(lambda: dict())\n'
            'collections.defaultdict(lambda: tuple())\n'
            'collections.defaultdict(lambda: [])\n'
            'collections.defaultdict(lambda: {})\n'
            'collections.defaultdict(lambda: "")\n'
            'collections.defaultdict(lambda: \'\')\n'
            'collections.defaultdict(lambda: 0)\n'
            'collections.defaultdict(lambda: 0.0)\n'
            'collections.defaultdict(lambda: 0.00000)\n'
            'collections.defaultdict(lambda: 0j)\n',
            'import collections\n\n'
            'collections.defaultdict(set)\n'
            'collections.defaultdict(list)\n'
            'collections.defaultdict(dict)\n'
            'collections.defaultdict(tuple)\n'
            'collections.defaultdict(list)\n'
            'collections.defaultdict(dict)\n'
            'collections.defaultdict(str)\n'
            'collections.defaultdict(str)\n'
            'collections.defaultdict(int)\n'
            'collections.defaultdict(float)\n'
            'collections.defaultdict(float)\n'
            'collections.defaultdict(complex)\n',
            id='call with attr',
        ),
    ),
)
def test_fix_defaultdict(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
