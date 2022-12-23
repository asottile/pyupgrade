from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    'src',
    ['A = type("A", (), {})', 'B = type("B", (int,), {}'],
)
def test_fix_type_bases_object_noop(src):
    ret = _fix_plugins(src, settings=Settings())
    assert ret == src
"""
pytest.param(
    'H = type(\n    "H",\n    (tuple, object),\n    {}\n)',
    'H = type(\n    "H",\n    (tuple,),\n    {}\n)',
    id='newline and indent, two base classes, object last',
),
pytest.param(
    'I = type(\n    "I",\n    (\n        class1,\n'
    '        class2,\n        class3,\n        class4,\n        class5'
    ',\n        class6,\n        class7,\n        class8,\n        '
    'class9,\n        classA,\n        object\n    ),\n    {}\n)',
    'I = type(\n    "I",\n    (\n        class1,\n        class2,\n'
    '        class3,\n        class4,\n        class5,\n        class6'
    ',\n        class7,\n        class8,\n        class9,\n        '
    'classA\n    ),\n    {}\n)',
    id='newline and also inside classes tuple, object last',
),
pytest.param(
    'J = type("J", (object, foo, bar,), {})',
    'J = type("J", (foo, bar,), {})',
    id='trailing comma, object first',
),
pytest.param(
    'K = type("K", (foo, bar, object,), {})',
    'K = type("K", (foo, bar,), {})',
    id='trailing comma, object last',
),
pytest.param(
    'L = type(\n    "L",\n    (foo, bar, object,),\n    {}\n)',
    'L = type(\n    "L",\n    (foo, bar,),\n    {}\n)',
    id='trailing comma, newline and indent, object last',
),
pytest.param(
    'M = type(\n    "M",\n    (\n        class1,\n'
    '        class2,\n        class3,\n        class4,\n        class5'
    ',\n        class6,\n        class7,\n        class8,\n        '
    'class9,\n        classA,\n        object,\n    ),\n    {}\n)',
    'M = type(\n    "M",\n    (\n        class1,\n        class2,\n'
    '        class3,\n        class4,\n        class5,\n        class6'
    ',\n        class7,\n        class8,\n        class9,\n        '
    'classA,\n    ),\n    {}\n)',
    id='trailing comma, '
       'newline and also inside classes tuple, '
       'object last',
),
pytest.param(
    'O = type("O", (foo, object, bar), {})',
    'O = type("O", (foo, bar), {})',
    id='object in the middle',
),
pytest.param(
    'P = type(    \n"P",\n    (\n        foo,\n        object,'
    '\n        bar\n    ),\n    {}\n)',
    'P = type(    \n"P",\n    (\n        foo,\n        bar\n    '
    '),\n    {}\n)',
    id='newline and also inside classes tuple, object in the middle',
),
pytest.param(
    'Q = type(\n    "Q",\n    (foo, object, bar),\n    {}\n)',
    'Q = type(\n    "Q",\n    (foo, bar),\n    {}\n)',
    id='newline and indent, object in the middle',
),
pytest.param(
    'R = type("R", (object,tuple), {})',
    'R = type("R", (tuple,), {})',
    id='no spaces, object first',
),
pytest.param(
    'S = type("S", (tuple,object), {})',
    'S = type("S", (tuple,), {})',
    id='no spaces, object last',
),
pytest.param(
    'U = type("U", (tuple, object,), {})',
    'U = type("U", (tuple,), {})',
    id='trailing comma, object last, two classes',
),
"""


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'A = type("A", (object,), {})',
            'A = type("A", (), {})',
            id='only object base class',
        ),
        pytest.param(
            'B = type("B", (object, tuple), {})',
            'B = type("B", (tuple,), {})',
            id='two base classes, object first',
        ),
        pytest.param(
            'C = type("C", (object, foo, bar), {})',
            'C = type("C", (foo, bar), {})',
            id='three base classes, object first',
        ),
        pytest.param(
            'D = type("D", (tuple, object), {})',
            'D = type("D", (tuple,), {})',
            id='two base classes, object last',
        ),
        pytest.param(
            'E = type("E", (foo, bar, object), {})',
            'E = type("E", (foo, bar), {})',
            id='three base classes, object last',
        ),
        pytest.param(
            'F = type(\n    "F",\n    (object, tuple),\n    {}\n)',
            'F = type(\n    "F",\n    (tuple,),\n    {}\n)',
            id='newline and indent, two base classes',
        ),
        pytest.param(
            'G = type(\n    "G",\n    (\n        object,\n        class1,\n'
            '        class2,\n        class3,\n        class4,\n        class5'
            ',\n        class6,\n        class7,\n        class8,\n        '
            'class9,\n        classA,\n        classB\n    ),\n    {}\n)',
            'G = type(\n    "G",\n    (\n        class1,\n        class2,\n'
            '        class3,\n        class4,\n        class5,\n        class6'
            ',\n        class7,\n        class8,\n        class9,\n        '
            'classA,\n        classB\n    ),\n    {}\n)',
            id='newline and  also inside classes tuple',
        ),
    ),
)
def test_fix_type_bases_object(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
