from __future__ import annotations

import pytest

from pyupgrade._main import _fix_plugins
from pyupgrade._main import Settings


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        'x(',

        'class C(Base):\n'
        '    def f(self):\n'
        '        super().f()\n',

        # super class doesn't match class name
        'class C(Base):\n'
        '    def f(self):\n'
        '        super(Base, self).f()\n',
        'class Outer:\n'  # common nesting
        '    class C(Base):\n'
        '        def f(self):\n'
        '            super(C, self).f()\n',
        'class Outer:\n'  # higher levels of nesting
        '    class Inner:\n'
        '        class C(Base):\n'
        '            def f(self):\n'
        '                super(Inner.C, self).f()\n',
        'class Outer:\n'  # super arg1 nested in unrelated name
        '    class C(Base):\n'
        '        def f(self):\n'
        '            super(some_module.Outer.C, self).f()\n',

        # super outside of a class (technically legal!)
        'def f(self):\n'
        '    super(C, self).f()\n',

        # super used in a comprehension
        'class C(Base):\n'
        '    def f(self):\n'
        '        return [super(C, self).f() for _ in ()]\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        return {super(C, self).f() for _ in ()}\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        return (super(C, self).f() for _ in ())\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        return {True: super(C, self).f() for _ in ()}\n',
        # nested comprehension
        'class C(Base):\n'
        '    def f(self):\n'
        '        return [\n'
        '            (\n'
        '                [_ for _ in ()],\n'
        '                super(C, self).f(),\n'
        '            )\n'
        '            for _ in ()'
        '        ]\n',
        # super in a closure
        'class C(Base):\n'
        '    def f(self):\n'
        '        def g():\n'
        '            super(C, self).f()\n'
        '        g()\n',
        'class C(Base):\n'
        '    def f(self):\n'
        '        g = lambda: super(C, self).f()\n'
        '        g()\n',
    ),
)
def test_fix_super_noop(s):
    assert _fix_plugins(s, settings=Settings()) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'class C(Base):\n'
            '    def f(self):\n'
            '        super(C, self).f()\n',
            'class C(Base):\n'
            '    def f(self):\n'
            '        super().f()\n',
        ),
        (
            'class C(Base):\n'
            '    def f(self):\n'
            '        super (C, self).f()\n',
            'class C(Base):\n'
            '    def f(self):\n'
            '        super().f()\n',
        ),
        (
            'class Outer:\n'
            '    class C(Base):\n'
            '        def f(self):\n'
            '            super (Outer.C, self).f()\n',
            'class Outer:\n'
            '    class C(Base):\n'
            '        def f(self):\n'
            '            super().f()\n',
        ),
        (
            'def f():\n'
            '    class Outer:\n'
            '        class C(Base):\n'
            '            def f(self):\n'
            '                super(Outer.C, self).f()\n',
            'def f():\n'
            '    class Outer:\n'
            '        class C(Base):\n'
            '            def f(self):\n'
            '                super().f()\n',
        ),
        (
            'class A:\n'
            '    class B:\n'
            '        class C:\n'
            '            def f(self):\n'
            '                super(A.B.C, self).f()\n',
            'class A:\n'
            '    class B:\n'
            '        class C:\n'
            '            def f(self):\n'
            '                super().f()\n',
        ),
        (
            'class C(Base):\n'
            '    f = lambda self: super(C, self).f()\n',
            'class C(Base):\n'
            '    f = lambda self: super().f()\n',
        ),
        (
            'class C(Base):\n'
            '    @classmethod\n'
            '    def f(cls):\n'
            '        super(C, cls).f()\n',
            'class C(Base):\n'
            '    @classmethod\n'
            '    def f(cls):\n'
            '        super().f()\n',
        ),
        pytest.param(
            'class C:\n'
            '    async def foo(self):\n'
            '        super(C, self).foo()\n',

            'class C:\n'
            '    async def foo(self):\n'
            '        super().foo()\n',

            id='async def super',
        ),
    ),
)
def test_fix_super(s, expected):
    assert _fix_plugins(s, settings=Settings()) == expected
