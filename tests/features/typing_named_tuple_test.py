import pytest

from pyupgrade._main import _fix_py36_plus


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
    assert _fix_py36_plus(s) == s


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
            # mypy treates Tuple[int] and Tuple[int,] the same so in practice
            # preserving this doesn't really matter
            'C = typing.NamedTuple("C", [("a", Tuple[int,])])',

            'class C(typing.NamedTuple):\n'
            '    a: Tuple[int,]',

            id='actually a tuple in generic argument',
        ),
    ),
)
def test_fix_typing_named_tuple(s, expected):
    assert _fix_py36_plus(s) == expected
