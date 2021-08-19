import ast
import functools
from typing import Iterable
from typing import Tuple

from tokenize_rt import Offset

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import replace_name


METHOD_MAPPING_PY27 = {
    'assertEquals': 'assertEqual',
    'failUnlessEqual': 'assertEqual',
    'failIfEqual': 'assertNotEqual',
    'failUnless': 'assertTrue',
    'assert_': 'assertTrue',
    'failIf': 'assertFalse',
    'failUnlessRaises': 'assertRaises',
    'failUnlessAlmostEqual': 'assertAlmostEqual',
    'failIfAlmostEqual': 'assertNotAlmostEqual',
}

METHOD_MAPPING_PY35_PLUS = {
    **METHOD_MAPPING_PY27,
    'assertNotEquals': 'assertNotEqual',
    'assertAlmostEquals': 'assertAlmostEqual',
    'assertNotAlmostEquals': 'assertNotAlmostEqual',
    'assertRegexpMatches': 'assertRegex',
    'assertNotRegexpMatches': 'assertNotRegex',
    'assertRaisesRegexp': 'assertRaisesRegex',
}


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[Tuple[Offset, TokenFunc]]:
    if state.settings.min_version >= (3,):
        method_mapping = METHOD_MAPPING_PY35_PLUS
    else:
        method_mapping = METHOD_MAPPING_PY27

    if (
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'self' and
            node.func.attr in method_mapping
    ):
        func = functools.partial(
            replace_name,
            name=node.func.attr,
            new=f'self.{method_mapping[node.func.attr]}',
        )
        yield ast_to_offset(node.func), func
