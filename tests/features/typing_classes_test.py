from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        '',

        pytest.param(
            'from typing import NamedTuple as wat\n'
            'C = wat("C", ("a", int))\n',
            id='currently not following as imports',
        ),

        pytest.param('C = typing.NamedTuple("C", ())', id='no types'),
        pytest.param('C = typing.NamedTuple("C")', id='not enough args'),
        pytest.param(
            'C = typing.NamedTuple("C", (), nonsense=1)',
            id='namedtuple with named args',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", {"foo": int, "bar": str})',
            id='namedtuple without a list/tuple',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [["a", str], ["b", int]])',
            id='namedtuple without inner tuples',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [(), ()])',
            id='namedtuple but inner tuples are incorrect length',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [(not_a_str, str)])',
            id='namedtuple but attribute name is not a string',
        ),

        pytest.param(
            'C = typing.NamedTuple("C", [("def", int)])',
            id='uses keyword',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [("not-ok", int)])',
            id='uses non-identifier',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", *types)',
            id='NamedTuple starargs',
        ),
        pytest.param(
            'from .typing import NamedTuple\n'
            'C = NamedTuple("C", [("a", int)])\n',
            id='relative imports',
        ),
    ),
)
def test_typing_named_tuple_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from typing import NamedTuple\n'
            'C = NamedTuple("C", [("a", int), ("b", str)])\n',

            'from typing import NamedTuple\n'
            'class C(NamedTuple):\n'
            '    a: int\n'
            '    b: str\n',
            id='typing from import',
        ),
        pytest.param(
            'import typing\n'
            'C = typing.NamedTuple("C", [("a", int), ("b", str)])\n',

            'import typing\n'
            'class C(typing.NamedTuple):\n'
            '    a: int\n'
            '    b: str\n',

            id='import typing',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [("a", List[int])])',

            'class C(typing.NamedTuple):\n'
            '    a: List[int]',

            id='generic attribute types',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [("a", Mapping[int, str])])',

            'class C(typing.NamedTuple):\n'
            '    a: Mapping[int, str]',

            id='generic attribute types with multi types',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [("a", "Queue[int]")])',

            'class C(typing.NamedTuple):\n'
            "    a: 'Queue[int]'",

            id='quoted type names',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [("a", Tuple[int, ...])])',

            'class C(typing.NamedTuple):\n'
            '    a: Tuple[int, ...]',

            id='type with ellipsis',
        ),
        pytest.param(
            'C = typing.NamedTuple("C", [("a", Callable[[Any], None])])',

            'class C(typing.NamedTuple):\n'
            '    a: Callable[[Any], None]',

            id='type containing a list',
        ),
        pytest.param(
            'if False:\n'
            '    pass\n'
            'C = typing.NamedTuple("C", [("a", int)])\n',

            'if False:\n'
            '    pass\n'
            'class C(typing.NamedTuple):\n'
            '    a: int\n',

            id='class directly after block',
        ),
        pytest.param(
            'if True:\n'
            '    C = typing.NamedTuple("C", [("a", int)])\n',

            'if True:\n'
            '    class C(typing.NamedTuple):\n'
            '        a: int\n',

            id='indented',
        ),
        pytest.param(
            'if True:\n'
            '    ...\n'
            '    C = typing.NamedTuple("C", [("a", int)])\n',

            'if True:\n'
            '    ...\n'
            '    class C(typing.NamedTuple):\n'
            '        a: int\n',

            id='indented, but on next line',
        ),
        pytest.param(
            # mypy treats Tuple[int] and Tuple[int,] the same so in practice
            # preserving this doesn't really matter
            'C = typing.NamedTuple("C", [("a", Tuple[int,])])',

            'class C(typing.NamedTuple):\n'
            '    a: Tuple[int,]',

            id='actually a tuple in generic argument',
        ),
        pytest.param(
            'from typing import NamedTuple\n'
            'C = NamedTuple(  # 1\n'
            '    # 2\n'
            '    "C",  # 3\n'
            '    # 4\n'
            '    [("x", "int")],  # 5\n'
            '    # 6\n'
            ')  # 7\n',

            'from typing import NamedTuple\n'
            'class C(NamedTuple):\n'
            '    # 1\n'
            '    # 2\n'
            '    # 3\n'
            '    # 4\n'
            "    x: 'int'  # 5\n"
            '    # 6\n'
            '    # 7\n',

            id='preserves comments in all positions',
        ),
        pytest.param(
            'from typing import NamedTuple, Optional\n'
            'DeferredNode = NamedTuple(\n'
            '    "DeferredNode",\n'
            '    [\n'
            '        ("active_typeinfo", Optional[int]),  # this member (and\n'
            '                                             # its semantics)\n'
            '    ]\n'
            ')\n',

            'from typing import NamedTuple, Optional\n'
            'class DeferredNode(NamedTuple):\n'
            '    active_typeinfo: Optional[int]  # this member (and\n'
            '    # its semantics)\n',

            id='preserves comments without alignment',
        ),
        pytest.param(
            'from typing import NamedTuple\n'
            'Foo = NamedTuple("Foo", [("union", str | None)])',

            'from typing import NamedTuple\n'
            'class Foo(NamedTuple):\n'
            '    union: str | None',

            id='BitOr unparse error',
        ),
    ),
)
def test_fix_typing_named_tuple(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == expected


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'from wat import TypedDict\n'
            'Q = TypedDict("Q")\n',
            id='from imported from elsewhere',
        ),
        pytest.param('D = typing.TypedDict("D")', id='no typed kwargs'),
        pytest.param('D = typing.TypedDict("D", {})', id='no typed args'),
        pytest.param('D = typing.TypedDict("D", {}, a=int)', id='both'),
        pytest.param('D = typing.TypedDict("D", 1)', id='not a dict'),
        pytest.param(
            'D = typing.TypedDict("D", {1: str})',
            id='key is not a string',
        ),
        pytest.param(
            'D = typing.TypedDict("D", {"a-b": str})',
            id='key is not an identifier',
        ),
        pytest.param(
            'D = typing.TypedDict("D", {"class": str})',
            id='key is a keyword',
        ),
        pytest.param(
            'D = typing.TypedDict("D", {**d, "a": str})',
            id='dictionary splat operator',
        ),
        pytest.param(
            'C = typing.TypedDict("C", *types)',
            id='starargs',
        ),
        pytest.param(
            'D = typing.TypedDict("D", **types)',
            id='starstarkwargs',
        ),
        pytest.param(
            'D = typing.TypedDict("D", x=int, total=False)',
            id='kw_typed_dict with total',
        ),
    ),
)
def test_typing_typed_dict_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from typing import TypedDict\n'
            'D = TypedDict("D", a=int)\n',

            'from typing import TypedDict\n'
            'class D(TypedDict):\n'
            '    a: int\n',

            id='keyword TypedDict from imported',
        ),
        pytest.param(
            'import typing\n'
            'D = typing.TypedDict("D", a=int)\n',

            'import typing\n'
            'class D(typing.TypedDict):\n'
            '    a: int\n',

            id='keyword TypedDict from attribute',
        ),
        pytest.param(
            'import typing\n'
            'D = typing.TypedDict("D", {"a": int})\n',

            'import typing\n'
            'class D(typing.TypedDict):\n'
            '    a: int\n',

            id='TypedDict from dict literal',
        ),
        pytest.param(
            'import typing\n'
            'D = typing.TypedDict("D", {"a": typing.Literal["b", b"c"]})\n',

            'import typing\n'
            'class D(typing.TypedDict):\n'
            "    a: typing.Literal['b', b'c']\n",

            id='with Literal of bytes',
        ),
        pytest.param(
            'import typing\n'
            'D = typing.TypedDict("D", {"a": int}, total=False)\n',

            'import typing\n'
            'class D(typing.TypedDict, total=False):\n'
            '    a: int\n',

            id='TypedDict from dict literal with total',
        ),
        pytest.param(
            'import typing\n'
            'D = typing.TypedDict("D", {\n'
            '    # first comment\n'
            '    "a": int,  # inline comment\n'
            '    # second comment\n'
            '    "b": str,\n'
            '    # third comment\n'
            '}, total=False)\n',

            'import typing\n'
            'class D(typing.TypedDict, total=False):\n'
            '    # first comment\n'
            '    a: int  # inline comment\n'
            '    # second comment\n'
            '    b: str\n'
            '    # third comment\n',

            id='preserves comments',
        ),
        pytest.param(
            'from typing_extensions import TypedDict\n'
            'D = TypedDict("D", a=int)\n',

            'from typing_extensions import TypedDict\n'
            'class D(TypedDict):\n'
            '    a: int\n',

            id='keyword TypedDict from typing_extensions',
        ),
        pytest.param(
            'import typing_extensions\n'
            'D = typing_extensions.TypedDict("D", {"a": int})\n',

            'import typing_extensions\n'
            'class D(typing_extensions.TypedDict):\n'
            '    a: int\n',

            id='dict TypedDict from typing_extensions',
        ),
        pytest.param(
            'import typing_extensions\n'
            'D = typing_extensions.TypedDict("D", {"a": int}, total=True)\n',

            'import typing_extensions\n'
            'class D(typing_extensions.TypedDict, total=True):\n'
            '    a: int\n',

            id='keyword TypedDict from typing_extensions, with total',
        ),
        pytest.param(
            'from typing import List\n'
            'from typing_extensions import TypedDict\n'
            'Foo = TypedDict("Foo", {"lsts": List[List[int]]})',

            'from typing import List\n'
            'from typing_extensions import TypedDict\n'
            'class Foo(TypedDict):\n'
            '    lsts: List[List[int]]',

            id='index unparse error',
        ),
        pytest.param(
            'import typing\n'
            'if True:\n'
            '    if False:\n'
            '        pass\n'
            '    D = typing.TypedDict("D", a=int)\n',

            'import typing\n'
            'if True:\n'
            '    if False:\n'
            '        pass\n'
            '    class D(typing.TypedDict):\n'
            '        a: int\n',

            id='right after a dedent',
        ),
        pytest.param(
            'from typing import TypedDict\n'
            'Foo = TypedDict("Foo", {"union": str | int | None})',

            'from typing import TypedDict\n'
            'class Foo(TypedDict):\n'
            '    union: str | int | None',

            id='BitOr unparse error',
        ),
    ),
)
def test_typing_typed_dict(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 6))) == expected
