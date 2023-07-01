from __future__ import annotations

import sys

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            'from typing import Literal\n'
            'x: "str"\n',
            id='missing __future__ import',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Literal["foo", "bar"]\n',
            id='Literal',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x = TypeVar("x", "str")\n',
            id='TypeVar',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x = cast(x, "str")\n',
            id='cast',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'X = List["MyClass"]\n',
            id='Alias',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'X: MyCallable("X")\n',
            id='Custom callable',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(x, *args, **kwargs): ...\n',
            id='Untyped',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(*, inplace): ...\n',
            id='Kwonly, untyped',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'x: Annotated[1:2] = ...\n',
            id='Annotated with invalid slice',
        ),
        pytest.param(
            'from __future__ import annotations\n'
            'def f[X](x: X) -> X: return x\n',
            id='TypeVar without bound',
        ),
    ),
)
def test_fix_typing_pep563_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


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
            'async def foo(var: "MyClass") -> "MyClass":\n'
            '   ...\n',

            'from __future__ import annotations\n'
            'async def foo(var: MyClass) -> MyClass:\n'
            '   ...\n',

            id='simple async annotation',
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
        pytest.param(
            'from __future__ import annotations\n'
            'def foo(var0, /, var1: "MyClass") -> "MyClass":\n'
            '   x: "MyClass"\n',

            'from __future__ import annotations\n'
            'def foo(var0, /, var1: MyClass) -> MyClass:\n'
            '   x: MyClass\n',

            id='posonly args',
        ),
    ),
)
def test_fix_typing_pep563(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 7)))
    assert ret == expected


@pytest.mark.xfail(sys.version_info < (3, 12), reason='3.12+ syntax')
def test_typevar_bound():
    src = '''\
from __future__ import annotations
def f[T: "int"](t: T) -> T:
    return t
'''
    expected = '''\
from __future__ import annotations
def f[T: int](t: T) -> T:
    return t
'''
    ret = _fix_plugins(src, settings=Settings())
    assert ret == expected
