import sys

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'from typing import Literal\n'
            'x: "str"\n',
            (2, 7),
            id='not python 3.11+',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Literal["foo", "bar"]\n',
            (3,),
            id='Literal',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x = TypeVar("x", "str")\n',
            (3,),
            id='TypeVar',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x = cast(x, "str")\n',
            (3,),
            id='cast',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'X = List["MyClass"]\n',
            (3,),
            id='Alias',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'X: MyCallable("X")\n',
            (3,),
            id='Custom callable',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(x, *args, **kwargs): ...\n',
            (3,),
            id='Untyped',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(*, inplace): ...\n',
            (3,),
            id='Kwonly, untyped',
        ),
    ),
)
def test_fix_typing_pep563_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(var: "MyClass") -> "MyClass":\n'
            '   x: "MyClass"\n',

            'from __future__ import annotations\n'
            'def foo(var: MyClass) -> MyClass:\n'
            '   x: MyClass\n',

            id='Simple annotation',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(*, inplace: "bool"): ...\n',

            'from __future__ import annotations\n'
            'def foo(*, inplace: bool): ...\n',

            id='Kwonly, typed',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(*args: "str", **kwargs: "int"): ...\n',

            'from __future__ import annotations\n'
            'def foo(*args: str, **kwargs: int): ...\n',

            id='Vararg and kwarg typed',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Tuple["MyClass"]\n',

            'from __future__ import annotations\n'
            'x: Tuple[MyClass]\n',

            id='Tuple',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Callable[["MyClass"], None]\n',

            'from __future__ import annotations\n'
            'x: Callable[[MyClass], None]\n',

            id='List within Callable',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'class Foo(NamedTuple):\n'
            '    x: "MyClass"\n',

            'from __future__ import annotations\n'
            'class Foo(NamedTuple):\n'
            '    x: MyClass\n',

            id='Inherit from NamedTuple',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'class D(TypedDict):\n'
            '    E: TypedDict("E", foo="int", total=False)\n',

            'from __future__ import annotations\n'
            'class D(TypedDict):\n'
            '    E: TypedDict("E", foo=int, total=False)\n',

            id='TypedDict keyword syntax',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'class D(TypedDict):\n'
            '    E: TypedDict("E", {"foo": "int"})\n',

            'from __future__ import annotations\n'
            'class D(TypedDict):\n'
            '    E: TypedDict("E", {"foo": int})\n',

            id='TypedDict dict syntax',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'class D(typing.TypedDict):\n'
            '    E: typing.TypedDict("E", {"foo": "int"})\n',

            'from __future__ import annotations\n'
            'class D(typing.TypedDict):\n'
            '    E: typing.TypedDict("E", {"foo": int})\n',

            id='typing.TypedDict',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'class D(TypedDict):\n'
            '    E: TypedDict("E")\n',

            'from __future__ import annotations\n'
            'class D(TypedDict):\n'
            '    E: TypedDict("E")\n',

            id='TypedDict no type (invalid syntax)',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Annotated["str", "metadata"]\n',

            'from __future__ import annotations\n'
            'x: Annotated[str, "metadata"]\n',

            id='Annotated',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: typing.Annotated["str", "metadata"]\n',

            'from __future__ import annotations\n'
            'x: typing.Annotated[str, "metadata"]\n',

            id='typing.Annotated',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Annotated[()]\n',

            'from __future__ import annotations\n'
            'x: Annotated[()]\n',

            id='Empty Annotated (garbage)',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Arg("str", "name")\n',

            'from __future__ import annotations\n'
            'x: Arg(str, "name")\n',

            id='Arg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: DefaultArg("str", "name")\n',

            'from __future__ import annotations\n'
            'x: DefaultArg(str, "name")\n',

            id='DefaultArg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedArg("str", "name")\n',

            'from __future__ import annotations\n'
            'x: NamedArg(str, "name")\n',

            id='NamedArg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: DefaultNamedArg("str", "name")\n',

            'from __future__ import annotations\n'
            'x: DefaultNamedArg(str, "name")\n',

            id='DefaultNamedArg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: DefaultNamedArg("str", name="name")\n',

            'from __future__ import annotations\n'
            'x: DefaultNamedArg(str, name="name")\n',

            id='DefaultNamedArg with one keyword argument',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: DefaultNamedArg(name="name", type="str")\n',

            'from __future__ import annotations\n'
            'x: DefaultNamedArg(name="name", type=str)\n',

            id='DefaultNamedArg with keyword arguments',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: DefaultNamedArg(name="name", quox="str")\n',

            'from __future__ import annotations\n'
            'x: DefaultNamedArg(name="name", quox="str")\n',

            id='DefaultNamedArg with invalid arguments',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: DefaultNamedArg(name="name")\n',

            'from __future__ import annotations\n'
            'x: DefaultNamedArg(name="name")\n',

            id='DefaultNamedArg with no type (invalid syntax)',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: VarArg("str")\n',

            'from __future__ import annotations\n'
            'x: VarArg(str)\n',

            id='VarArg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: List[List[List["MyClass"]]]\n',

            'from __future__ import annotations\n'
            'x: List[List[List[MyClass]]]\n',

            id='Nested',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedTuple("X", [("foo", "int"), ("bar", "str")])\n',

            'from __future__ import annotations\n'
            'x: NamedTuple("X", [("foo", int), ("bar", str)])\n',

            id='NamedTuple with types, no kwarg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedTuple("X", fields=[("foo", "int"), ("bar", "str")])\n',

            'from __future__ import annotations\n'
            'x: NamedTuple("X", fields=[("foo", int), ("bar", str)])\n',

            id='NamedTuple with types, one kwarg',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedTuple(typename="X", fields=[("foo", "int")])\n',

            'from __future__ import annotations\n'
            'x: NamedTuple(typename="X", fields=[("foo", int)])\n',

            id='NamedTuple with types, two kwargs',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedTuple("X", [("foo",), ("bar",)])\n',

            'from __future__ import annotations\n'
            'x: NamedTuple("X", [("foo",), ("bar",)])\n',

            id='NamedTuple with length-1 tuples (invalid syntax)',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedTuple("X", ["foo", "bar"])\n',

            'from __future__ import annotations\n'
            'x: NamedTuple("X", ["foo", "bar"])\n',

            id='NamedTuple with missing types (invalid syntax)',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: NamedTuple()\n',

            'from __future__ import annotations\n'
            'x: NamedTuple()\n',

            id='NamedTuple with no args (invalid syntax)',
        ),
    ),
)
def test_fix_typing_pep563(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 7)))
    assert ret == expected


def test_replaced_for_minimum_version():
    ret = _fix_plugins('x: "int"', settings=Settings(min_version=(3, 11)))
    assert ret == 'x: int'


@pytest.mark.xfail(
    sys.version_info < (3, 8),
    reason='posonly args not available in Python3.7',
)
def test_fix_typing_pep563_posonlyargs():
    s = (
        'from __future__ import annotations\n'
        'def foo(var0, /, var1: "MyClass") -> "MyClass":\n'
        '   x: "MyClass"\n'
    )
    expected = (
        'from __future__ import annotations\n'
        'def foo(var0, /, var1: MyClass) -> MyClass:\n'
        '   x: MyClass\n'
    )
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 8)))
    assert ret == expected
