import ast
from typing import cast
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Type
from typing import Union

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import is_name_attr
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._data import Version
from pyupgrade._token_helpers import Block


def _find_if_else_block(tokens: List[Token], i: int) -> Tuple[Block, Block]:
    if_block = Block.find(tokens, i)
    i = if_block.end
    while tokens[i].src != 'else':
        i += 1
    else_block = Block.find(tokens, i, trim_end=True)
    return if_block, else_block


def _find_elif(tokens: List[Token], i: int) -> int:
    while tokens[i].src != 'elif':  # pragma: no cover (only for <3.8.1)
        i -= 1
    return i


def _fix_py3_block(i: int, tokens: List[Token]) -> None:
    if tokens[i].src == 'if':
        if_block = Block.find(tokens, i)
        if_block.dedent(tokens)
        del tokens[if_block.start:if_block.block]
    else:
        if_block = Block.find(tokens, _find_elif(tokens, i))
        if_block.replace_condition(tokens, [Token('NAME', 'else')])


def _fix_py2_block(i: int, tokens: List[Token]) -> None:
    if tokens[i].src == 'if':
        if_block, else_block = _find_if_else_block(tokens, i)
        else_block.dedent(tokens)
        del tokens[if_block.start:else_block.block]
    else:
        j = _find_elif(tokens, i)
        if_block, else_block = _find_if_else_block(tokens, j)
        del tokens[if_block.start:else_block.start]


def _fix_py3_block_else(i: int, tokens: List[Token]) -> None:
    if tokens[i].src == 'if':
        if_block, else_block = _find_if_else_block(tokens, i)
        if_block.dedent(tokens)
        del tokens[if_block.end:else_block.end]
        del tokens[if_block.start:if_block.block]
    else:
        j = _find_elif(tokens, i)
        if_block, else_block = _find_if_else_block(tokens, j)
        del tokens[if_block.end:else_block.end]
        if_block.replace_condition(tokens, [Token('NAME', 'else')])


def _eq(test: ast.Compare, n: int) -> bool:
    return (
        isinstance(test.ops[0], ast.Eq) and
        isinstance(test.comparators[0], ast.Num) and
        test.comparators[0].n == n
    )


def _compare_to_3(
    test: ast.Compare,
    op: Union[Type[ast.cmpop], Tuple[Type[ast.cmpop], ...]],
    minor: int = 0,
) -> bool:
    if not (
            isinstance(test.ops[0], op) and
            isinstance(test.comparators[0], ast.Tuple) and
            len(test.comparators[0].elts) >= 1 and
            all(isinstance(n, ast.Num) for n in test.comparators[0].elts)
    ):
        return False

    # checked above but mypy needs help
    ast_elts = cast('List[ast.Num]', test.comparators[0].elts)
    # padding a 0 for compatibility with (3,) used as a spec
    elts = tuple(e.n for e in ast_elts) + (0,)

    return elts[:2] == (3, minor) and all(n == 0 for n in elts[2:])


@register(ast.If)
def visit_If(
        state: State,
        node: ast.If,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:

    min_version: Version
    if state.settings.min_version == (3,):
        min_version = (3, 0)
    else:
        min_version = state.settings.min_version
    assert len(min_version) >= 2

    if (
            min_version >= (3,) and (
                # if six.PY2:
                is_name_attr(node.test, state.from_imports, 'six', ('PY2',)) or
                # if not six.PY3:
                (
                    isinstance(node.test, ast.UnaryOp) and
                    isinstance(node.test.op, ast.Not) and
                    is_name_attr(
                        node.test.operand,
                        state.from_imports,
                        'six',
                        ('PY3',),
                    )
                ) or
                # sys.version_info == 2 or < (3,)
                # or < (3, n) or <= (3, n) (with n<m)
                (
                    isinstance(node.test, ast.Compare) and
                    is_name_attr(
                        node.test.left,
                        state.from_imports,
                        'sys',
                        ('version_info',),
                    ) and
                    len(node.test.ops) == 1 and (
                        _eq(node.test, 2) or
                        _compare_to_3(node.test, ast.Lt, min_version[1]) or
                        any(
                            _compare_to_3(node.test, (ast.Lt, ast.LtE), minor)
                            for minor in range(min_version[1])
                        )
                    )
                )
            )
    ):
        if node.orelse and not isinstance(node.orelse[0], ast.If):
            yield ast_to_offset(node), _fix_py2_block
    elif (
            min_version >= (3,) and (
                # if six.PY3:
                is_name_attr(node.test, state.from_imports, 'six', ('PY3',)) or
                # if not six.PY2:
                (
                    isinstance(node.test, ast.UnaryOp) and
                    isinstance(node.test.op, ast.Not) and
                    is_name_attr(
                        node.test.operand,
                        state.from_imports,
                        'six',
                        ('PY2',),
                    )
                ) or
                # sys.version_info == 3 or >= (3,) or > (3,)
                # sys.version_info >= (3, n) (with n<=m)
                # or sys.version_info > (3, n) (with n<m)
                (
                    isinstance(node.test, ast.Compare) and
                    is_name_attr(
                        node.test.left,
                        state.from_imports,
                        'sys',
                        ('version_info',),
                    ) and
                    len(node.test.ops) == 1 and (
                        _eq(node.test, 3) or
                        _compare_to_3(node.test, (ast.Gt, ast.GtE)) or
                        _compare_to_3(node.test, ast.GtE, min_version[1]) or
                        any(
                            _compare_to_3(node.test, (ast.Gt, ast.GtE), minor)
                            for minor in range(min_version[1])
                        )
                    )
                )
            )
    ):
        if node.orelse and not isinstance(node.orelse[0], ast.If):
            yield ast_to_offset(node), _fix_py3_block_else
        elif not node.orelse:
            yield ast_to_offset(node), _fix_py3_block
