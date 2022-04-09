from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from collections import (Counter, \n'
            '                         Mapping)\n',
            'from collections import (Counter, \n'
            '                         Mapping)\n',
            id='parenthesized imports not supported',
        ),
        pytest.param(
            'from collections import Counter, \\\n'
            '                        Mapping\n',
            'from collections import Counter, \\\n'
            '                        Mapping\n',
            id='\\ continuations in imports not supported',
        ),
        pytest.param(
            'from collections import Set as MySet\n'
            'import sys',
            'from collections import Set as MySet\n'
            'import sys',
            id='import ABC as other name not supported',
        ),
        pytest.param(
            'try:\n'
            '    from queue import Queue\n'
            'except ImportError:\n'
            '    pass\n'
            '\n'
            'from collections import namedtuple, defaultdict, Iterable\n'
            'from timeit import default_timer\n'
            '\n',
            'try:\n'
            '    from queue import Queue\n'
            'except ImportError:\n'
            '    pass\n'
            '\n'
            'from collections import namedtuple, defaultdict\n'
            'from collections.abc import Iterable\n'
            'from timeit import default_timer\n'
            '\n',
            id='complex failure example involving presence of DEDENT token',
        ),
        pytest.param(
            'from collections import Set\n'
            'import sys',
            'from collections.abc import Set\n'
            'import sys',
            id='Set alone followed by other statements',
        ),
        pytest.param(
            'from collections import defaultdict, Set\n'
            'import sys',
            'from collections import defaultdict\n'
            'from collections.abc import Set\n'
            'import sys',
            id='defaultdict and Set followed by other statements',
        ),
        pytest.param(
            'from collections import MutableMapping, Mapping',
            'from collections.abc import MutableMapping, Mapping',
            id='MutableMapping',
        ),
        pytest.param(
            'from collections import Counter, MutableMapping, deque',
            'from collections import Counter, deque\n'
            'from collections.abc import MutableMapping'
            ,
            id='MutableMapping_with_deque',
        ),
        pytest.param(
            'from collections import Counter, MutableMapping, deque\n'
            'pass',
            'from collections import Counter, deque\n'
            'from collections.abc import MutableMapping\n'
            'pass'
            ,
            id='MutableMapping_with_deque_and_pass',
        ),
        pytest.param(
            'from collections import Generator\n'
            '\n'
            'isinstance(g, Generator)',
            'from collections.abc import Generator\n'
            '\n'
            'isinstance(g, Generator)',
            id='relative import class',
        ),
        pytest.param(
            'import collections\n'
            '\n'
            'isinstance(g, collections.Generator)',
            'import collections\n'
            '\n'
            'isinstance(g, collections.abc.Generator)',
            id='reference from collections',
        ),
        pytest.param(
            'from collections import Generator, Awaitable, KeysView\n'
            '\n'
            'isinstance(g, collections.Generator)\n'
            'isinstance(a, collections.Awaitable)\n'
            'isinstance(kv, collections.KeysView)\n',
            'from collections.abc import Generator, Awaitable, KeysView\n'
            '\n'
            'isinstance(g, collections.abc.Generator)\n'
            'isinstance(a, collections.abc.Awaitable)\n'
            'isinstance(kv, collections.abc.KeysView)\n',
            id='multiple relative import classes',
        ),
        pytest.param(
            'def fn():\n'
            '    from collections import Counter, MutableMapping, deque\n'
            '    a = 1000',
            'def fn():\n'
            '    from collections import Counter, deque\n'
            '    from collections.abc import MutableMapping\n'
            '    a = 1000',
            id='imports nested in a function',
        ),
        pytest.param(
            'if isinstance(x, collections.Sized):\n'
            '    print(len(x))\n',
            'if isinstance(x, collections.abc.Sized):\n'
            '    print(len(x))\n',
            id='Attribute reference for Sized class',
        ),
    ),
)
def test_fix_abc_import_from_collections(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 3)))
    assert ret == expected
