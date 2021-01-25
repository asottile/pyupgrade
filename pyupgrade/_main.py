import argparse
import ast
import codecs
import collections
import contextlib
import re
import string
import sys
import tokenize
from typing import Any
from typing import cast
from typing import Container
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List
from typing import Match
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import Type
from typing import Union

from tokenize_rt import NON_CODING_TOKENS
from tokenize_rt import Offset
from tokenize_rt import parse_string_literal
from tokenize_rt import reversed_enumerate
from tokenize_rt import rfind_string_parts
from tokenize_rt import src_to_tokens
from tokenize_rt import Token
from tokenize_rt import tokens_to_src
from tokenize_rt import UNIMPORTANT_WS

from pyupgrade._ast_helpers import ast_parse
from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._data import FUNCS
from pyupgrade._data import Version
from pyupgrade._data import visit
from pyupgrade._string_helpers import is_ascii
from pyupgrade._token_helpers import arg_str
from pyupgrade._token_helpers import CLOSING
from pyupgrade._token_helpers import find_end
from pyupgrade._token_helpers import find_open_paren
from pyupgrade._token_helpers import find_token
from pyupgrade._token_helpers import KEYWORDS
from pyupgrade._token_helpers import OPENING
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import remove_brace
from pyupgrade._token_helpers import remove_decorator
from pyupgrade._token_helpers import replace_call
from pyupgrade._token_helpers import victims

DotFormatPart = Tuple[str, Optional[str], Optional[str], Optional[str]]

NameOrAttr = Union[ast.Name, ast.Attribute]
AnyFunctionDef = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda]
SyncFunctionDef = Union[ast.FunctionDef, ast.Lambda]

_stdlib_parse_format = string.Formatter().parse

_EXPR_NEEDS_PARENS: Tuple[Type[ast.expr], ...] = (
    ast.Await, ast.BinOp, ast.BoolOp, ast.Compare, ast.GeneratorExp, ast.IfExp,
    ast.Lambda, ast.UnaryOp,
)
if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    _EXPR_NEEDS_PARENS += (ast.NamedExpr,)


def parse_format(s: str) -> Tuple[DotFormatPart, ...]:
    """Makes the empty string not a special case.  In the stdlib, there's
    loss of information (the type) on the empty string.
    """
    parsed = tuple(_stdlib_parse_format(s))
    if not parsed:
        return ((s, None, None, None),)
    else:
        return parsed


def unparse_parsed_string(parsed: Sequence[DotFormatPart]) -> str:
    def _convert_tup(tup: DotFormatPart) -> str:
        ret, field_name, format_spec, conversion = tup
        ret = ret.replace('{', '{{')
        ret = ret.replace('}', '}}')
        if field_name is not None:
            ret += '{' + field_name
            if conversion:
                ret += '!' + conversion
            if format_spec:
                ret += ':' + format_spec
            ret += '}'
        return ret

    return ''.join(_convert_tup(tup) for tup in parsed)


def inty(s: str) -> bool:
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def _fix_plugins(
        contents_text: str,
        *,
        min_version: Version,
        keep_percent_format: bool,
) -> str:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    callbacks = visit(
        FUNCS,
        ast_obj,
        min_version=min_version,
        keep_percent_format=keep_percent_format,
    )

    if not callbacks:
        return contents_text

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:  # pragma: no cover (bpo-2180)
        return contents_text

    for i, token in reversed_enumerate(tokens):
        if not token.src:
            continue
        # though this is a defaultdict, by using `.get()` this function's
        # self time is almost 50% faster
        for callback in callbacks.get(token.offset, ()):
            callback(i, tokens)

    return tokens_to_src(tokens)


def _imports_future(contents_text: str, future_name: str) -> bool:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return False

    for node in ast_obj.body:
        # Docstring
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            continue
        elif isinstance(node, ast.ImportFrom):
            if (
                node.level == 0 and
                node.module == '__future__' and
                any(name.name == future_name for name in node.names)
            ):
                return True
            elif node.module == '__future__':
                continue
            else:
                return False
        else:
            return False

    return False


# https://docs.python.org/3/reference/lexical_analysis.html
ESCAPE_STARTS = frozenset((
    '\n', '\r', '\\', "'", '"', 'a', 'b', 'f', 'n', 'r', 't', 'v',
    '0', '1', '2', '3', '4', '5', '6', '7',  # octal escapes
    'x',  # hex escapes
))
ESCAPE_RE = re.compile(r'\\.', re.DOTALL)
NAMED_ESCAPE_NAME = re.compile(r'\{[^}]+\}')


def _fix_escape_sequences(token: Token) -> Token:
    prefix, rest = parse_string_literal(token.src)
    actual_prefix = prefix.lower()

    if 'r' in actual_prefix or '\\' not in rest:
        return token

    is_bytestring = 'b' in actual_prefix

    def _is_valid_escape(match: Match[str]) -> bool:
        c = match.group()[1]
        return (
            c in ESCAPE_STARTS or
            (not is_bytestring and c in 'uU') or
            (
                not is_bytestring and
                c == 'N' and
                bool(NAMED_ESCAPE_NAME.match(rest, match.end()))
            )
        )

    has_valid_escapes = False
    has_invalid_escapes = False
    for match in ESCAPE_RE.finditer(rest):
        if _is_valid_escape(match):
            has_valid_escapes = True
        else:
            has_invalid_escapes = True

    def cb(match: Match[str]) -> str:
        matched = match.group()
        if _is_valid_escape(match):
            return matched
        else:
            return fr'\{matched}'

    if has_invalid_escapes and (has_valid_escapes or 'u' in actual_prefix):
        return token._replace(src=prefix + ESCAPE_RE.sub(cb, rest))
    elif has_invalid_escapes and not has_valid_escapes:
        return token._replace(src=prefix + 'r' + rest)
    else:
        return token


def _remove_u_prefix(token: Token) -> Token:
    prefix, rest = parse_string_literal(token.src)
    if 'u' not in prefix.lower():
        return token
    else:
        new_prefix = prefix.replace('u', '').replace('U', '')
        return token._replace(src=new_prefix + rest)


def _fix_ur_literals(token: Token) -> Token:
    prefix, rest = parse_string_literal(token.src)
    if prefix.lower() != 'ur':
        return token
    else:
        def cb(match: Match[str]) -> str:
            escape = match.group()
            if escape[1].lower() == 'u':
                return escape
            else:
                return '\\' + match.group()

        rest = ESCAPE_RE.sub(cb, rest)
        prefix = prefix.replace('r', '').replace('R', '')
        return token._replace(src=prefix + rest)


def _fix_long(src: str) -> str:
    return src.rstrip('lL')


def _fix_octal(s: str) -> str:
    if not s.startswith('0') or not s.isdigit() or s == len(s) * '0':
        return s
    elif len(s) == 2:
        return s[1:]
    else:
        return '0o' + s[1:]


def _fix_extraneous_parens(tokens: List[Token], i: int) -> None:
    # search forward for another non-coding token
    i += 1
    while tokens[i].name in NON_CODING_TOKENS:
        i += 1
    # if we did not find another brace, return immediately
    if tokens[i].src != '(':
        return

    start = i
    depth = 1
    while depth:
        i += 1
        # found comma or yield at depth 1: this is a tuple / coroutine
        if depth == 1 and tokens[i].src in {',', 'yield'}:
            return
        elif tokens[i].src in OPENING:
            depth += 1
        elif tokens[i].src in CLOSING:
            depth -= 1
    end = i

    # empty tuple
    if all(t.name in NON_CODING_TOKENS for t in tokens[start + 1:i]):
        return

    # search forward for the next non-coding token
    i += 1
    while tokens[i].name in NON_CODING_TOKENS:
        i += 1

    if tokens[i].src == ')':
        remove_brace(tokens, end)
        remove_brace(tokens, start)


def _remove_fmt(tup: DotFormatPart) -> DotFormatPart:
    if tup[1] is None:
        return tup
    else:
        return (tup[0], '', tup[2], tup[3])


def _fix_format_literal(tokens: List[Token], end: int) -> None:
    parts = rfind_string_parts(tokens, end)
    parsed_parts = []
    last_int = -1
    for i in parts:
        # f'foo {0}'.format(...) would get turned into a SyntaxError
        prefix, _ = parse_string_literal(tokens[i].src)
        if 'f' in prefix.lower():
            return

        try:
            parsed = parse_format(tokens[i].src)
        except ValueError:
            # the format literal was malformed, skip it
            return

        # The last segment will always be the end of the string and not a
        # format, slice avoids the `None` format key
        for _, fmtkey, spec, _ in parsed[:-1]:
            if (
                    fmtkey is not None and inty(fmtkey) and
                    int(fmtkey) == last_int + 1 and
                    spec is not None and '{' not in spec
            ):
                last_int += 1
            else:
                return

        parsed_parts.append(tuple(_remove_fmt(tup) for tup in parsed))

    for i, parsed in zip(parts, parsed_parts):
        tokens[i] = tokens[i]._replace(src=unparse_parsed_string(parsed))


def _fix_encode_to_binary(tokens: List[Token], i: int) -> None:
    # .encode()
    if (
            i + 2 < len(tokens) and
            tokens[i + 1].src == '(' and
            tokens[i + 2].src == ')'
    ):
        victims = slice(i - 1, i + 3)
        latin1_ok = False
    # .encode('encoding')
    elif (
            i + 3 < len(tokens) and
            tokens[i + 1].src == '(' and
            tokens[i + 2].name == 'STRING' and
            tokens[i + 3].src == ')'
    ):
        victims = slice(i - 1, i + 4)
        prefix, rest = parse_string_literal(tokens[i + 2].src)
        if 'f' in prefix.lower():
            return
        encoding = ast.literal_eval(prefix + rest)
        if _is_codec(encoding, 'ascii') or _is_codec(encoding, 'utf-8'):
            latin1_ok = False
        elif _is_codec(encoding, 'iso8859-1'):
            latin1_ok = True
        else:
            return
    else:
        return

    parts = rfind_string_parts(tokens, i - 2)
    if not parts:
        return

    for part in parts:
        prefix, rest = parse_string_literal(tokens[part].src)
        escapes = set(ESCAPE_RE.findall(rest))
        if (
                not is_ascii(rest) or
                '\\u' in escapes or
                '\\U' in escapes or
                '\\N' in escapes or
                ('\\x' in escapes and not latin1_ok) or
                'f' in prefix.lower()
        ):
            return

    for part in parts:
        prefix, rest = parse_string_literal(tokens[part].src)
        prefix = 'b' + prefix.replace('u', '').replace('U', '')
        tokens[part] = tokens[part]._replace(src=prefix + rest)
    del tokens[victims]


def _build_import_removals() -> Dict[Version, Dict[str, Tuple[str, ...]]]:
    ret = {}
    future: Tuple[Tuple[Version, Tuple[str, ...]], ...] = (
        ((2, 7), ('nested_scopes', 'generators', 'with_statement')),
        (
            (3,), (
                'absolute_import', 'division', 'print_function',
                'unicode_literals',
            ),
        ),
        ((3, 6), ()),
        ((3, 7), ('generator_stop',)),
        ((3, 8), ()),
        ((3, 9), ()),
    )

    prev: Tuple[str, ...] = ()
    for min_version, names in future:
        prev += names
        ret[min_version] = {'__future__': prev}
    # see reorder_python_imports
    for k, v in ret.items():
        if k >= (3,):
            v.update({
                'builtins': (
                    'ascii', 'bytes', 'chr', 'dict', 'filter', 'hex', 'input',
                    'int', 'list', 'map', 'max', 'min', 'next', 'object',
                    'oct', 'open', 'pow', 'range', 'round', 'str', 'super',
                    'zip', '*',
                ),
                'io': ('open',),
                'six': ('callable', 'next'),
                'six.moves': ('filter', 'input', 'map', 'range', 'zip'),
            })
    return ret


IMPORT_REMOVALS = _build_import_removals()


def _fix_import_removals(
        tokens: List[Token],
        start: int,
        min_version: Version,
) -> None:
    i = start + 1
    name_parts = []
    while tokens[i].src != 'import':
        if tokens[i].name in {'NAME', 'OP'}:
            name_parts.append(tokens[i].src)
        i += 1

    modname = ''.join(name_parts)
    if modname not in IMPORT_REMOVALS[min_version]:
        return

    found: List[Optional[int]] = []
    i += 1
    while tokens[i].name not in {'NEWLINE', 'ENDMARKER'}:
        if tokens[i].name == 'NAME' or tokens[i].src == '*':
            # don't touch aliases
            if (
                    found and found[-1] is not None and
                    tokens[found[-1]].src == 'as'
            ):
                found[-2:] = [None]
            else:
                found.append(i)
        i += 1
    # depending on the version of python, some will not emit NEWLINE('') at the
    # end of a file which does not end with a newline (for example 3.6.5)
    if tokens[i].name == 'ENDMARKER':  # pragma: no cover
        i -= 1

    remove_names = IMPORT_REMOVALS[min_version][modname]
    to_remove = [
        x for x in found if x is not None and tokens[x].src in remove_names
    ]
    if len(to_remove) == len(found):
        del tokens[start:i + 1]
    else:
        for idx in reversed(to_remove):
            if found[0] == idx:  # look forward until next name and del
                j = idx + 1
                while tokens[j].name != 'NAME':
                    j += 1
                del tokens[idx:j]
            else:  # look backward for comma and del
                j = idx
                while tokens[j].src != ',':
                    j -= 1
                del tokens[j:idx + 1]


def _fix_tokens(contents_text: str, min_version: Version) -> str:
    remove_u = (
        min_version >= (3,) or
        _imports_future(contents_text, 'unicode_literals')
    )

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:
        return contents_text
    for i, token in reversed_enumerate(tokens):
        if token.name == 'NUMBER':
            tokens[i] = token._replace(src=_fix_long(_fix_octal(token.src)))
        elif token.name == 'STRING':
            tokens[i] = _fix_ur_literals(tokens[i])
            if remove_u:
                tokens[i] = _remove_u_prefix(tokens[i])
            tokens[i] = _fix_escape_sequences(tokens[i])
        elif token.src == '(':
            _fix_extraneous_parens(tokens, i)
        elif token.src == 'format' and i > 0 and tokens[i - 1].src == '.':
            _fix_format_literal(tokens, i - 2)
        elif token.src == 'encode' and i > 0 and tokens[i - 1].src == '.':
            _fix_encode_to_binary(tokens, i)
        elif (
                min_version >= (3,) and
                token.utf8_byte_offset == 0 and
                token.line < 3 and
                token.name == 'COMMENT' and
                tokenize.cookie_re.match(token.src)
        ):
            del tokens[i]
            assert tokens[i].name == 'NL', tokens[i].name
            del tokens[i]
        elif token.src == 'from' and token.utf8_byte_offset == 0:
            _fix_import_removals(tokens, i, min_version)
    return tokens_to_src(tokens).lstrip()


SIX_SIMPLE_ATTRS = {
    'text_type': 'str',
    'binary_type': 'bytes',
    'class_types': '(type,)',
    'string_types': '(str,)',
    'integer_types': '(int,)',
    'unichr': 'chr',
    'iterbytes': 'iter',
    'print_': 'print',
    'exec_': 'exec',
    'advance_iterator': 'next',
    'next': 'next',
    'callable': 'callable',
}
SIX_TYPE_CTX_ATTRS = {
    'class_types': 'type',
    'string_types': 'str',
    'integer_types': 'int',
}
SIX_CALLS = {
    'u': '{args[0]}',
    'byte2int': '{args[0]}[0]',
    'indexbytes': '{args[0]}[{rest}]',
    'iteritems': '{args[0]}.items()',
    'iterkeys': '{args[0]}.keys()',
    'itervalues': '{args[0]}.values()',
    'viewitems': '{args[0]}.items()',
    'viewkeys': '{args[0]}.keys()',
    'viewvalues': '{args[0]}.values()',
    'create_unbound_method': '{args[0]}',
    'get_unbound_function': '{args[0]}',
    'get_method_function': '{args[0]}.__func__',
    'get_method_self': '{args[0]}.__self__',
    'get_function_closure': '{args[0]}.__closure__',
    'get_function_code': '{args[0]}.__code__',
    'get_function_defaults': '{args[0]}.__defaults__',
    'get_function_globals': '{args[0]}.__globals__',
    'assertCountEqual': '{args[0]}.assertCountEqual({rest})',
    'assertRaisesRegex': '{args[0]}.assertRaisesRegex({rest})',
    'assertRegex': '{args[0]}.assertRegex({rest})',
}
SIX_INT2BYTE_TMPL = 'bytes(({args[0]},))'
WITH_METACLASS_NO_BASES_TMPL = 'metaclass={args[0]}'
WITH_METACLASS_BASES_TMPL = '{rest}, metaclass={args[0]}'
RAISE_FROM_TMPL = 'raise {args[0]} from {rest}'
RERAISE_TMPL = 'raise'
RERAISE_2_TMPL = 'raise {args[1]}.with_traceback(None)'
RERAISE_3_TMPL = 'raise {args[1]}.with_traceback({args[2]})'
SIX_NATIVE_STR = frozenset(('ensure_str', 'ensure_text', 'text_type'))
U_MODE_REMOVE = frozenset(('U', 'Ur', 'rU', 'r', 'rt', 'tr'))
U_MODE_REPLACE_R = frozenset(('Ub', 'bU'))
U_MODE_REMOVE_U = frozenset(('rUb', 'Urb', 'rbU', 'Ubr', 'bUr', 'brU'))
U_MODE_REPLACE = U_MODE_REPLACE_R | U_MODE_REMOVE_U

PEP585_BUILTINS = {
    k: k.lower()
    for k in ('Dict', 'FrozenSet', 'List', 'Set', 'Tuple', 'Type')
}


def _all_isinstance(
        vals: Iterable[Any],
        tp: Union[Type[Any], Tuple[Type[Any], ...]],
) -> bool:
    return all(isinstance(v, tp) for v in vals)


def fields_same(n1: ast.AST, n2: ast.AST) -> bool:
    for (a1, v1), (a2, v2) in zip(ast.iter_fields(n1), ast.iter_fields(n2)):
        # ignore ast attributes, they'll be covered by walk
        if a1 != a2:
            return False
        elif _all_isinstance((v1, v2), ast.AST):
            continue
        elif _all_isinstance((v1, v2), (list, tuple)):
            if len(v1) != len(v2):
                return False
            # ignore sequences which are all-ast, they'll be covered by walk
            elif _all_isinstance(v1, ast.AST) and _all_isinstance(v2, ast.AST):
                continue
            elif v1 != v2:
                return False
        elif v1 != v2:
            return False
    return True


def targets_same(target: ast.AST, yield_value: ast.AST) -> bool:
    for t1, t2 in zip(ast.walk(target), ast.walk(yield_value)):
        # ignore `ast.Load` / `ast.Store`
        if _all_isinstance((t1, t2), ast.expr_context):
            continue
        elif type(t1) != type(t2):
            return False
        elif not fields_same(t1, t2):
            return False
    else:
        return True


def _is_codec(encoding: str, name: str) -> bool:
    try:
        return codecs.lookup(encoding).name == name
    except LookupError:
        return False


class FindPy3Plus(ast.NodeVisitor):
    OS_ERROR_ALIASES = frozenset((
        'EnvironmentError',
        'IOError',
        'WindowsError',
    ))

    OS_ERROR_ALIAS_MODULES = frozenset((
        'mmap',
        'select',
        'socket',
    ))

    FROM_IMPORTED_MODULES = OS_ERROR_ALIAS_MODULES.union((
        'functools', 'six', 'typing',
    ))

    MOCK_MODULES = frozenset(('mock', 'mock.mock'))

    class ClassInfo:
        def __init__(self, name: str) -> None:
            self.name = name
            self.def_depth = 0
            self.first_arg_name = ''

    class Scope:
        def __init__(self) -> None:
            self.reads: Set[str] = set()
            self.writes: Set[str] = set()

            self.yield_from_fors: Set[Offset] = set()
            self.yield_from_names: Dict[str, Set[Offset]]
            self.yield_from_names = collections.defaultdict(set)

    def __init__(self, version: Tuple[int, ...], keep_mock: bool) -> None:
        self._version = version
        self._find_mock = not keep_mock

        self.encode_calls: Dict[Offset, ast.Call] = {}

        self._exc_info_imported = False
        self._version_info_imported = False
        self.if_py3_blocks: Set[Offset] = set()
        self.if_py2_blocks_else: Set[Offset] = set()
        self.if_py3_blocks_else: Set[Offset] = set()

        self.native_literals: Set[Offset] = set()

        self._from_imports: Dict[str, Set[str]] = collections.defaultdict(set)
        self.io_open_calls: Set[Offset] = set()
        self.mock_mock: Set[Offset] = set()
        self.mock_absolute_imports: Set[Offset] = set()
        self.mock_relative_imports: Set[Offset] = set()
        self.open_mode_calls: Set[Offset] = set()
        self.os_error_alias_calls: Set[Offset] = set()
        self.os_error_alias_simple: Dict[Offset, NameOrAttr] = {}
        self.os_error_alias_excepts: Set[Offset] = set()

        self.six_add_metaclass: Set[Offset] = set()
        self.six_calls: Dict[Offset, ast.Call] = {}
        self.six_calls_int2byte: Set[Offset] = set()
        self.six_iter: Dict[Offset, ast.Call] = {}
        self._previous_node: Optional[ast.AST] = None
        self.six_raise_from: Set[Offset] = set()
        self.six_reraise: Set[Offset] = set()
        self.six_simple: Dict[Offset, NameOrAttr] = {}
        self.six_type_ctx: Dict[Offset, NameOrAttr] = {}
        self.six_with_metaclass: Set[Offset] = set()

        self._in_type_annotation = False
        self.typing_builtin_renames: Dict[Offset, NameOrAttr] = {}

        self._class_info_stack: List[FindPy3Plus.ClassInfo] = []
        self._in_comp = 0
        self.super_calls: Dict[Offset, ast.Call] = {}
        self._in_async_def = False
        self._scope_stack: List[FindPy3Plus.Scope] = []
        self.yield_from_fors: Set[Offset] = set()

    def _is_six(self, node: ast.expr, names: Container[str]) -> bool:
        return (
            isinstance(node, ast.Name) and
            node.id in names and
            node.id in self._from_imports['six']
        ) or (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'six' and
            node.attr in names
        )

    def _is_star_sys_exc_info(self, node: ast.Call) -> bool:
        return (
            len(node.args) == 1 and
            isinstance(node.args[0], ast.Starred) and
            isinstance(node.args[0].value, ast.Call) and
            self._is_exc_info(node.args[0].value.func)
        )

    def _is_mock_mock(self, node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'mock' and
            node.attr == 'mock'
        )

    def _is_io_open(self, node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'io' and
            node.attr == 'open'
        )

    def _is_os_error_alias(self, node: Optional[ast.expr]) -> bool:
        return (
            isinstance(node, ast.Name) and
            node.id in self.OS_ERROR_ALIASES
        ) or (
            isinstance(node, ast.Name) and
            node.id == 'error' and
            (
                node.id in self._from_imports['mmap'] or
                node.id in self._from_imports['select'] or
                node.id in self._from_imports['socket']
            )
        ) or (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id in self.OS_ERROR_ALIAS_MODULES and
            node.attr == 'error'
        )

    def _is_exc_info(self, node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Name) and
            node.id == 'exc_info' and
            self._exc_info_imported
        ) or (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'sys' and
            node.attr == 'exc_info'
        )

    def _is_version_info(self, node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Name) and
            node.id == 'version_info' and
            self._version_info_imported
        ) or (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'sys' and
            node.attr == 'version_info'
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.level:
            if node.module in self.FROM_IMPORTED_MODULES:
                for name in node.names:
                    if not name.asname:
                        self._from_imports[node.module].add(name.name)
            elif self._find_mock and node.module in self.MOCK_MODULES:
                self.mock_relative_imports.add(ast_to_offset(node))
            elif node.module == 'sys' and any(
                name.name == 'exc_info' and not name.asname
                for name in node.names
            ):
                self._exc_info_imported = True
            elif node.module == 'sys' and any(
                name.name == 'version_info' and not name.asname
                for name in node.names
            ):
                self._version_info_imported = True
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if (
                self._find_mock and
                len(node.names) == 1 and
                node.names[0].name in self.MOCK_MODULES
        ):
            self.mock_absolute_imports.add(ast_to_offset(node))

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            if (
                    isinstance(decorator, ast.Call) and
                    self._is_six(decorator.func, ('add_metaclass',)) and
                    not has_starargs(decorator)
            ):
                self.six_add_metaclass.add(ast_to_offset(decorator))

        if (
                len(node.bases) == 1 and
                isinstance(node.bases[0], ast.Call) and
                self._is_six(node.bases[0].func, ('with_metaclass',)) and
                not has_starargs(node.bases[0])
        ):
            self.six_with_metaclass.add(ast_to_offset(node.bases[0]))

        self._class_info_stack.append(FindPy3Plus.ClassInfo(node.name))
        self.generic_visit(node)
        self._class_info_stack.pop()

    @contextlib.contextmanager
    def _track_def_depth(
            self,
            node: AnyFunctionDef,
    ) -> Generator[None, None, None]:
        class_info = self._class_info_stack[-1]
        class_info.def_depth += 1
        if class_info.def_depth == 1 and node.args.args:
            class_info.first_arg_name = node.args.args[0].arg
        try:
            yield
        finally:
            class_info.def_depth -= 1

    @contextlib.contextmanager
    def _scope(self) -> Generator[None, None, None]:
        self._scope_stack.append(FindPy3Plus.Scope())
        try:
            yield
        finally:
            info = self._scope_stack.pop()
            # discard any that were referenced outside of the loop
            for name in info.reads:
                offsets = info.yield_from_names[name]
                info.yield_from_fors.difference_update(offsets)
            self.yield_from_fors.update(info.yield_from_fors)
            if self._scope_stack:
                cell_reads = info.reads - info.writes
                self._scope_stack[-1].reads.update(cell_reads)

    def _visit_annotation(self, node: ast.AST) -> None:
        orig, self._in_type_annotation = self._in_type_annotation, True
        self.generic_visit(node)
        self._in_type_annotation = orig

    def _visit_func(self, node: AnyFunctionDef) -> None:
        with contextlib.ExitStack() as ctx, self._scope():
            if self._class_info_stack:
                ctx.enter_context(self._track_def_depth(node))

            if not isinstance(node, ast.Lambda) and node.returns is not None:
                self._visit_annotation(node.returns)

            self.generic_visit(node)

    def _visit_sync_func(self, node: SyncFunctionDef) -> None:
        self._in_async_def, orig = False, self._in_async_def
        self._visit_func(node)
        self._in_async_def = orig

    visit_FunctionDef = visit_Lambda = _visit_sync_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._in_async_def, orig = True, self._in_async_def
        self._visit_func(node)
        self._in_async_def = orig

    def visit_arg(self, node: ast.arg) -> None:
        if node.annotation is not None:
            self._visit_annotation(node.annotation)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._visit_annotation(node.annotation)
        self.generic_visit(node)

    def _visit_comp(self, node: ast.expr) -> None:
        self._in_comp += 1
        with self._scope():
            self.generic_visit(node)
        self._in_comp -= 1

    visit_ListComp = visit_SetComp = _visit_comp
    visit_DictComp = visit_GeneratorExp = _visit_comp

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._is_six(node, SIX_SIMPLE_ATTRS):
            self.six_simple[ast_to_offset(node)] = node
        elif self._find_mock and self._is_mock_mock(node):
            self.mock_mock.add(ast_to_offset(node))
        elif (
                (
                    self._version >= (3, 9) or
                    self._in_type_annotation
                ) and
                isinstance(node.value, ast.Name) and
                node.value.id == 'typing' and
                node.attr in PEP585_BUILTINS
        ):
            self.typing_builtin_renames[ast_to_offset(node)] = node
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if self._is_six(node, SIX_SIMPLE_ATTRS):
            self.six_simple[ast_to_offset(node)] = node
        elif (
                (
                    self._version >= (3, 9) or
                    self._in_type_annotation
                ) and
                node.id in PEP585_BUILTINS and
                node.id in self._from_imports['typing']
        ):
            self.typing_builtin_renames[ast_to_offset(node)] = node

        if self._scope_stack:
            if isinstance(node.ctx, ast.Load):
                self._scope_stack[-1].reads.add(node.id)
            elif isinstance(node.ctx, (ast.Store, ast.Del)):
                self._scope_stack[-1].writes.add(node.id)
            else:
                raise AssertionError(node)

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        for handler in node.handlers:
            htype = handler.type
            if self._is_os_error_alias(htype):
                assert isinstance(htype, (ast.Name, ast.Attribute))
                self.os_error_alias_simple[ast_to_offset(htype)] = htype
            elif (
                    isinstance(htype, ast.Tuple) and
                    any(
                        self._is_os_error_alias(elt)
                        for elt in htype.elts
                    )
            ):
                self.os_error_alias_excepts.add(ast_to_offset(htype))

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        exc = node.exc

        if exc is not None and self._is_os_error_alias(exc):
            assert isinstance(exc, (ast.Name, ast.Attribute))
            self.os_error_alias_simple[ast_to_offset(exc)] = exc
        elif (
                isinstance(exc, ast.Call) and
                self._is_os_error_alias(exc.func)
        ):
            self.os_error_alias_calls.add(ast_to_offset(exc))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
                isinstance(node.func, ast.Name) and
                node.func.id in {'isinstance', 'issubclass'} and
                len(node.args) == 2 and
                self._is_six(node.args[1], SIX_TYPE_CTX_ATTRS)
        ):
            arg = node.args[1]
            # _is_six() enforces this
            assert isinstance(arg, (ast.Name, ast.Attribute))
            self.six_type_ctx[ast_to_offset(node.args[1])] = arg
        elif (
                self._is_six(node.func, SIX_CALLS) and
                node.args and
                not has_starargs(node)
        ):
            self.six_calls[ast_to_offset(node)] = node
        elif (
                self._is_six(node.func, ('int2byte',)) and
                node.args and
                not has_starargs(node)
        ):
            self.six_calls_int2byte.add(ast_to_offset(node))
        elif (
                isinstance(node.func, ast.Name) and
                node.func.id == 'next' and
                not has_starargs(node) and
                len(node.args) == 1 and
                isinstance(node.args[0], ast.Call) and
                self._is_six(
                    node.args[0].func,
                    ('iteritems', 'iterkeys', 'itervalues'),
                ) and
                not has_starargs(node.args[0])
        ):
            self.six_iter[ast_to_offset(node.args[0])] = node.args[0]
        elif (
                isinstance(self._previous_node, ast.Expr) and
                self._is_six(node.func, ('raise_from',)) and
                not has_starargs(node)
        ):
            self.six_raise_from.add(ast_to_offset(node))
        elif (
                isinstance(self._previous_node, ast.Expr) and
                self._is_six(node.func, ('reraise',)) and
                (not has_starargs(node) or self._is_star_sys_exc_info(node))
        ):
            self.six_reraise.add(ast_to_offset(node))
        elif (
                not self._in_comp and
                self._class_info_stack and
                self._class_info_stack[-1].def_depth == 1 and
                isinstance(node.func, ast.Name) and
                node.func.id == 'super' and
                len(node.args) == 2 and
                isinstance(node.args[0], ast.Name) and
                isinstance(node.args[1], ast.Name) and
                node.args[0].id == self._class_info_stack[-1].name and
                node.args[1].id == self._class_info_stack[-1].first_arg_name
        ):
            self.super_calls[ast_to_offset(node)] = node
        elif (
                (
                    self._is_six(node.func, SIX_NATIVE_STR) or
                    isinstance(node.func, ast.Name) and node.func.id == 'str'
                ) and
                not node.keywords and
                not has_starargs(node) and
                (
                    len(node.args) == 0 or
                    (
                        len(node.args) == 1 and
                        isinstance(node.args[0], ast.Str)
                    )
                )
        ):
            self.native_literals.add(ast_to_offset(node))
        elif (
                isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Str) and
                node.func.attr == 'encode' and
                not has_starargs(node) and
                len(node.args) == 1 and
                isinstance(node.args[0], ast.Str) and
                _is_codec(node.args[0].s, 'utf-8')
        ):
            self.encode_calls[ast_to_offset(node)] = node
        elif self._is_io_open(node.func):
            self.io_open_calls.add(ast_to_offset(node))
        elif (
                isinstance(node.func, ast.Name) and
                node.func.id == 'open' and
                not has_starargs(node) and
                len(node.args) >= 2 and
                isinstance(node.args[1], ast.Str) and (
                    node.args[1].s in U_MODE_REPLACE or
                    (len(node.args) == 2 and node.args[1].s in U_MODE_REMOVE)
                )
        ):
            self.open_mode_calls.add(ast_to_offset(node))

        self.generic_visit(node)

    @staticmethod
    def _eq(test: ast.Compare, n: int) -> bool:
        return (
            isinstance(test.ops[0], ast.Eq) and
            isinstance(test.comparators[0], ast.Num) and
            test.comparators[0].n == n
        )

    @staticmethod
    def _compare_to_3(
        test: ast.Compare,
        op: Union[Type[ast.cmpop], Tuple[Type[ast.cmpop], ...]],
    ) -> bool:
        if not (
                isinstance(test.ops[0], op) and
                isinstance(test.comparators[0], ast.Tuple) and
                len(test.comparators[0].elts) >= 1 and
                all(isinstance(n, ast.Num) for n in test.comparators[0].elts)
        ):
            return False

        # checked above but mypy needs help
        elts = cast('List[ast.Num]', test.comparators[0].elts)

        return elts[0].n == 3 and all(n.n == 0 for n in elts[1:])

    def visit_If(self, node: ast.If) -> None:
        if (
                # if six.PY2:
                self._is_six(node.test, ('PY2',)) or
                # if not six.PY3:
                (
                    isinstance(node.test, ast.UnaryOp) and
                    isinstance(node.test.op, ast.Not) and
                    self._is_six(node.test.operand, ('PY3',))
                ) or
                # sys.version_info == 2 or < (3,)
                (
                    isinstance(node.test, ast.Compare) and
                    self._is_version_info(node.test.left) and
                    len(node.test.ops) == 1 and (
                        self._eq(node.test, 2) or
                        self._compare_to_3(node.test, ast.Lt)
                    )
                )
        ):
            if node.orelse and not isinstance(node.orelse[0], ast.If):
                self.if_py2_blocks_else.add(ast_to_offset(node))
        elif (
                # if six.PY3:
                self._is_six(node.test, 'PY3') or
                # if not six.PY2:
                (
                    isinstance(node.test, ast.UnaryOp) and
                    isinstance(node.test.op, ast.Not) and
                    self._is_six(node.test.operand, ('PY2',))
                ) or
                # sys.version_info == 3 or >= (3,) or > (3,)
                (
                    isinstance(node.test, ast.Compare) and
                    self._is_version_info(node.test.left) and
                    len(node.test.ops) == 1 and (
                        self._eq(node.test, 3) or
                        self._compare_to_3(node.test, (ast.Gt, ast.GtE))
                    )
                )
        ):
            if node.orelse and not isinstance(node.orelse[0], ast.If):
                self.if_py3_blocks_else.add(ast_to_offset(node))
            elif not node.orelse:
                self.if_py3_blocks.add(ast_to_offset(node))
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        if (
            not self._in_async_def and
            len(node.body) == 1 and
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Yield) and
            node.body[0].value.value is not None and
            targets_same(node.target, node.body[0].value.value) and
            not node.orelse
        ):
            offset = ast_to_offset(node)
            func_info = self._scope_stack[-1]
            func_info.yield_from_fors.add(offset)
            for target_node in ast.walk(node.target):
                if (
                        isinstance(target_node, ast.Name) and
                        isinstance(target_node.ctx, ast.Store)
                ):
                    func_info.yield_from_names[target_node.id].add(offset)
            # manually visit, but with target+body as a separate scope
            self.visit(node.iter)
            with self._scope():
                self.visit(node.target)
                for stmt in node.body:
                    self.visit(stmt)
                assert not node.orelse
        else:
            self.generic_visit(node)

    def generic_visit(self, node: ast.AST) -> None:
        self._previous_node = node
        super().generic_visit(node)


def _fixup_dedent_tokens(tokens: List[Token]) -> None:
    """For whatever reason the DEDENT / UNIMPORTANT_WS tokens are misordered

    | if True:
    |     if True:
    |         pass
    |     else:
    |^    ^- DEDENT
    |+----UNIMPORTANT_WS
    """
    for i, token in enumerate(tokens):
        if token.name == UNIMPORTANT_WS and tokens[i + 1].name == 'DEDENT':
            tokens[i], tokens[i + 1] = tokens[i + 1], tokens[i]


def _find_block_start(tokens: List[Token], i: int) -> int:
    depth = 0
    while depth or tokens[i].src != ':':
        if tokens[i].src in OPENING:
            depth += 1
        elif tokens[i].src in CLOSING:
            depth -= 1
        i += 1
    return i


class Block(NamedTuple):
    start: int
    colon: int
    block: int
    end: int
    line: bool

    def _initial_indent(self, tokens: List[Token]) -> int:
        if tokens[self.start].src.isspace():
            return len(tokens[self.start].src)
        else:
            return 0

    def _minimum_indent(self, tokens: List[Token]) -> int:
        block_indent = None
        for i in range(self.block, self.end):
            if (
                    tokens[i - 1].name in ('NL', 'NEWLINE') and
                    tokens[i].name in ('INDENT', UNIMPORTANT_WS)
            ):
                token_indent = len(tokens[i].src)
                if block_indent is None:
                    block_indent = token_indent
                else:
                    block_indent = min(block_indent, token_indent)

        assert block_indent is not None
        return block_indent

    def dedent(self, tokens: List[Token]) -> None:
        if self.line:
            return
        diff = self._minimum_indent(tokens) - self._initial_indent(tokens)
        for i in range(self.block, self.end):
            if (
                    tokens[i - 1].name in ('DEDENT', 'NL', 'NEWLINE') and
                    tokens[i].name in ('INDENT', UNIMPORTANT_WS)
            ):
                tokens[i] = tokens[i]._replace(src=tokens[i].src[diff:])

    def replace_condition(self, tokens: List[Token], new: List[Token]) -> None:
        tokens[self.start:self.colon] = new

    def _trim_end(self, tokens: List[Token]) -> 'Block':
        """the tokenizer reports the end of the block at the beginning of
        the next block
        """
        i = last_token = self.end - 1
        while tokens[i].name in NON_CODING_TOKENS | {'DEDENT', 'NEWLINE'}:
            # if we find an indented comment inside our block, keep it
            if (
                    tokens[i].name in {'NL', 'NEWLINE'} and
                    tokens[i + 1].name == UNIMPORTANT_WS and
                    len(tokens[i + 1].src) > self._initial_indent(tokens)
            ):
                break
            # otherwise we've found another line to remove
            elif tokens[i].name in {'NL', 'NEWLINE'}:
                last_token = i
            i -= 1
        return self._replace(end=last_token + 1)

    @classmethod
    def find(
            cls,
            tokens: List[Token],
            i: int,
            trim_end: bool = False,
    ) -> 'Block':
        if i > 0 and tokens[i - 1].name in {'INDENT', UNIMPORTANT_WS}:
            i -= 1
        start = i
        colon = _find_block_start(tokens, i)

        j = colon + 1
        while (
                tokens[j].name != 'NEWLINE' and
                tokens[j].name in NON_CODING_TOKENS
        ):
            j += 1

        if tokens[j].name == 'NEWLINE':  # multi line block
            block = j + 1
            while tokens[j].name != 'INDENT':
                j += 1
            level = 1
            j += 1
            while level:
                level += {'INDENT': 1, 'DEDENT': -1}.get(tokens[j].name, 0)
                j += 1
            ret = cls(start, colon, block, j, line=False)
            if trim_end:
                return ret._trim_end(tokens)
            else:
                return ret
        else:  # single line block
            block = j
            j = find_end(tokens, j)
            return cls(start, colon, block, j, line=True)


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


def _get_tmpl(mapping: Dict[str, str], node: NameOrAttr) -> str:
    if isinstance(node, ast.Name):
        return mapping[node.id]
    else:
        return mapping[node.attr]


def _replace_yield(tokens: List[Token], i: int) -> None:
    in_token = find_token(tokens, i, 'in')
    colon = _find_block_start(tokens, i)
    block = Block.find(tokens, i, trim_end=True)
    container = tokens_to_src(tokens[in_token + 1:colon]).strip()
    tokens[i:block.end] = [Token('CODE', f'yield from {container}\n')]


def _fix_py3_plus(
        contents_text: str,
        min_version: Version,
        keep_mock: bool = False,
) -> str:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    pep585_rewrite = (
        min_version >= (3, 9) or
        _imports_future(contents_text, 'annotations')
    )

    visitor = FindPy3Plus(min_version, keep_mock)
    visitor.visit(ast_obj)

    if not any((
            visitor.encode_calls,
            visitor.if_py2_blocks_else,
            visitor.if_py3_blocks,
            visitor.if_py3_blocks_else,
            visitor.native_literals,
            visitor.io_open_calls,
            visitor.open_mode_calls,
            visitor.mock_mock,
            visitor.mock_absolute_imports,
            visitor.mock_relative_imports,
            visitor.os_error_alias_calls,
            visitor.os_error_alias_simple,
            visitor.os_error_alias_excepts,
            visitor.six_add_metaclass,
            visitor.six_calls,
            visitor.six_calls_int2byte,
            visitor.six_iter,
            visitor.six_raise_from,
            visitor.six_reraise,
            visitor.six_simple,
            visitor.six_type_ctx,
            visitor.six_with_metaclass,
            visitor.super_calls,
            visitor.typing_builtin_renames,
            visitor.yield_from_fors,
    )):
        return contents_text

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:  # pragma: no cover (bpo-2180)
        return contents_text

    _fixup_dedent_tokens(tokens)

    def _replace(i: int, mapping: Dict[str, str], node: NameOrAttr) -> None:
        new_token = Token('CODE', _get_tmpl(mapping, node))
        if isinstance(node, ast.Name):
            tokens[i] = new_token
        else:
            j = i
            while tokens[j].src != node.attr:
                # timid: if we see a parenthesis here, skip it
                if tokens[j].src == ')':
                    return
                j += 1
            tokens[i:j + 1] = [new_token]

    for i, token in reversed_enumerate(tokens):
        if not token.src:
            continue
        elif token.offset in visitor.if_py3_blocks:
            if tokens[i].src == 'if':
                if_block = Block.find(tokens, i)
                if_block.dedent(tokens)
                del tokens[if_block.start:if_block.block]
            else:
                if_block = Block.find(tokens, _find_elif(tokens, i))
                if_block.replace_condition(tokens, [Token('NAME', 'else')])
        elif token.offset in visitor.if_py2_blocks_else:
            if tokens[i].src == 'if':
                if_block, else_block = _find_if_else_block(tokens, i)
                else_block.dedent(tokens)
                del tokens[if_block.start:else_block.block]
            else:
                j = _find_elif(tokens, i)
                if_block, else_block = _find_if_else_block(tokens, j)
                del tokens[if_block.start:else_block.start]
        elif token.offset in visitor.if_py3_blocks_else:
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
        elif token.offset in visitor.native_literals:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            if any(tok.name == 'NL' for tok in tokens[i:end]):
                continue
            if func_args:
                replace_call(tokens, i, end, func_args, '{args[0]}')
            else:
                tokens[i:end] = [token._replace(name='STRING', src="''")]
        elif token.offset in visitor.six_type_ctx:
            _replace(i, SIX_TYPE_CTX_ATTRS, visitor.six_type_ctx[token.offset])
        elif token.offset in visitor.six_simple:
            _replace(i, SIX_SIMPLE_ATTRS, visitor.six_simple[token.offset])
        elif token.offset in visitor.six_iter:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            call = visitor.six_iter[token.offset]
            assert isinstance(call.func, (ast.Name, ast.Attribute))
            template = f'iter({_get_tmpl(SIX_CALLS, call.func)})'
            replace_call(tokens, i, end, func_args, template)
        elif token.offset in visitor.six_calls:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            call = visitor.six_calls[token.offset]
            assert isinstance(call.func, (ast.Name, ast.Attribute))
            template = _get_tmpl(SIX_CALLS, call.func)
            if isinstance(call.args[0], _EXPR_NEEDS_PARENS):
                replace_call(tokens, i, end, func_args, template, parens=(0,))
            else:
                replace_call(tokens, i, end, func_args, template)
        elif token.offset in visitor.six_calls_int2byte:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            replace_call(tokens, i, end, func_args, SIX_INT2BYTE_TMPL)
        elif token.offset in visitor.six_raise_from:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            replace_call(tokens, i, end, func_args, RAISE_FROM_TMPL)
        elif token.offset in visitor.six_reraise:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            if len(func_args) == 1:
                tmpl = RERAISE_TMPL
            elif len(func_args) == 2:
                tmpl = RERAISE_2_TMPL
            else:
                tmpl = RERAISE_3_TMPL
            replace_call(tokens, i, end, func_args, tmpl)
        elif token.offset in visitor.six_add_metaclass:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            metaclass = f'metaclass={arg_str(tokens, *func_args[0])}'
            # insert `metaclass={args[0]}` into `class:`
            # search forward for the `class` token
            j = i + 1
            while tokens[j].src != 'class':
                j += 1
            class_token = j
            # then search forward for a `:` token, not inside a brace
            j = _find_block_start(tokens, j)
            last_paren = -1
            for k in range(class_token, j):
                if tokens[k].src == ')':
                    last_paren = k

            if last_paren == -1:
                tokens.insert(j, Token('CODE', f'({metaclass})'))
            else:
                insert = last_paren - 1
                while tokens[insert].name in NON_CODING_TOKENS:
                    insert -= 1
                if tokens[insert].src == '(':  # no bases
                    src = metaclass
                elif tokens[insert].src != ',':
                    src = f', {metaclass}'
                else:
                    src = f' {metaclass},'
                tokens.insert(insert + 1, Token('CODE', src))
            remove_decorator(i, tokens)
        elif token.offset in visitor.six_with_metaclass:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            if len(func_args) == 1:
                tmpl = WITH_METACLASS_NO_BASES_TMPL
            elif len(func_args) == 2:
                base = arg_str(tokens, *func_args[1])
                if base == 'object':
                    tmpl = WITH_METACLASS_NO_BASES_TMPL
                else:
                    tmpl = WITH_METACLASS_BASES_TMPL
            else:
                tmpl = WITH_METACLASS_BASES_TMPL
            replace_call(tokens, i, end, func_args, tmpl)
        elif pep585_rewrite and token.offset in visitor.typing_builtin_renames:
            node = visitor.typing_builtin_renames[token.offset]
            _replace(i, PEP585_BUILTINS, node)
        elif token.offset in visitor.super_calls:
            i = find_open_paren(tokens, i)
            call = visitor.super_calls[token.offset]
            super_victims = victims(tokens, i, call, gen=False)
            del tokens[super_victims.starts[0] + 1:super_victims.ends[-1]]
        elif token.offset in visitor.encode_calls:
            i = find_open_paren(tokens, i + 1)
            call = visitor.encode_calls[token.offset]
            encode_victims = victims(tokens, i, call, gen=False)
            del tokens[encode_victims.starts[0] + 1:encode_victims.ends[-1]]
        elif token.offset in visitor.io_open_calls:
            j = find_open_paren(tokens, i)
            tokens[i:j] = [token._replace(name='NAME', src='open')]
        elif token.offset in visitor.mock_mock:
            j = find_token(tokens, i + 1, 'mock')
            del tokens[i + 1:j + 1]
        elif token.offset in visitor.mock_absolute_imports:
            j = find_token(tokens, i, 'mock')
            if (
                    j + 2 < len(tokens) and
                    tokens[j + 1].src == '.' and
                    tokens[j + 2].src == 'mock'
            ):
                j += 2
            src = 'from unittest import mock'
            tokens[i:j + 1] = [tokens[j]._replace(name='NAME', src=src)]
        elif token.offset in visitor.mock_relative_imports:
            j = find_token(tokens, i, 'mock')
            if (
                    j + 2 < len(tokens) and
                    tokens[j + 1].src == '.' and
                    tokens[j + 2].src == 'mock'
            ):
                k = j + 2
            else:
                k = j
            src = 'unittest.mock'
            tokens[j:k + 1] = [tokens[j]._replace(name='NAME', src=src)]
        elif token.offset in visitor.open_mode_calls:
            j = find_open_paren(tokens, i)
            func_args, end = parse_call_args(tokens, j)
            mode = tokens_to_src(tokens[slice(*func_args[1])])
            mode_stripped = mode.strip().strip('"\'')
            if mode_stripped in U_MODE_REMOVE:
                del tokens[func_args[0][1]:func_args[1][1]]
            elif mode_stripped in U_MODE_REPLACE_R:
                new_mode = mode.replace('U', 'r')
                tokens[slice(*func_args[1])] = [Token('SRC', new_mode)]
            elif mode_stripped in U_MODE_REMOVE_U:
                new_mode = mode.replace('U', '')
                tokens[slice(*func_args[1])] = [Token('SRC', new_mode)]
            else:
                raise AssertionError(f'unreachable: {mode!r}')
        elif token.offset in visitor.os_error_alias_calls:
            j = find_open_paren(tokens, i)
            tokens[i:j] = [token._replace(name='NAME', src='OSError')]
        elif token.offset in visitor.os_error_alias_simple:
            node = visitor.os_error_alias_simple[token.offset]
            _replace(i, collections.defaultdict(lambda: 'OSError'), node)
        elif token.offset in visitor.os_error_alias_excepts:
            line, utf8_byte_offset = token.line, token.utf8_byte_offset

            # find all the arg strs in the tuple
            except_index = i
            while tokens[except_index].src != 'except':
                except_index -= 1
            start = find_open_paren(tokens, except_index)
            func_args, end = parse_call_args(tokens, start)

            # save the exceptions and remove the block
            arg_strs = [arg_str(tokens, *arg) for arg in func_args]
            del tokens[start:end]

            # rewrite the block without dupes
            args = []
            for arg in arg_strs:
                left, part, right = arg.partition('.')
                if (
                        left in visitor.OS_ERROR_ALIAS_MODULES and
                        part == '.' and
                        right == 'error'
                ):
                    args.append('OSError')
                elif (
                        left in visitor.OS_ERROR_ALIASES and
                        part == right == ''
                ):
                    args.append('OSError')
                elif (
                        left == 'error' and
                        part == right == '' and
                        (
                            'error' in visitor._from_imports['mmap'] or
                            'error' in visitor._from_imports['select'] or
                            'error' in visitor._from_imports['socket']
                        )
                ):
                    args.append('OSError')
                else:
                    args.append(arg)

            unique_args = tuple(collections.OrderedDict.fromkeys(args))

            if len(unique_args) > 1:
                joined = '({})'.format(', '.join(unique_args))
            elif tokens[start - 1].name != 'UNIMPORTANT_WS':
                joined = ' {}'.format(unique_args[0])
            else:
                joined = unique_args[0]

            new = Token('CODE', joined, line, utf8_byte_offset)
            tokens.insert(start, new)

            visitor.os_error_alias_excepts.discard(token.offset)
        elif token.offset in visitor.yield_from_fors:
            _replace_yield(tokens, i)

    return tokens_to_src(tokens)


def _simple_arg(arg: ast.expr) -> bool:
    return (
        isinstance(arg, ast.Name) or
        (isinstance(arg, ast.Attribute) and _simple_arg(arg.value)) or
        (
            isinstance(arg, ast.Call) and
            _simple_arg(arg.func) and
            not arg.args and not arg.keywords
        )
    )


def _format_params(call: ast.Call) -> Dict[str, str]:
    params = {}
    for i, arg in enumerate(call.args):
        params[str(i)] = _unparse(arg)
    for kwd in call.keywords:
        # kwd.arg can't be None here because we exclude starargs
        assert kwd.arg is not None
        params[kwd.arg] = _unparse(kwd.value)
    return params


class FindPy36Plus(ast.NodeVisitor):
    def __init__(self) -> None:
        self.fstrings: Dict[Offset, ast.Call] = {}
        self.named_tuples: Dict[Offset, ast.Call] = {}
        self.dict_typed_dicts: Dict[Offset, ast.Call] = {}
        self.kw_typed_dicts: Dict[Offset, ast.Call] = {}
        self._from_imports: Dict[str, Set[str]] = collections.defaultdict(set)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module in {'typing', 'typing_extensions'}:
            for name in node.names:
                if not name.asname:
                    self._from_imports[node.module].add(name.name)
        self.generic_visit(node)

    def _is_attr(self, node: ast.AST, mods: Set[str], name: str) -> bool:
        return (
            (
                isinstance(node, ast.Name) and
                node.id == name and
                any(name in self._from_imports[mod] for mod in mods)
            ) or
            (
                isinstance(node, ast.Attribute) and
                node.attr == name and
                isinstance(node.value, ast.Name) and
                node.value.id in mods
            )
        )

    def _parse(self, node: ast.Call) -> Optional[Tuple[DotFormatPart, ...]]:
        if not (
                isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Str) and
                node.func.attr == 'format' and
                all(_simple_arg(arg) for arg in node.args) and
                all(_simple_arg(k.value) for k in node.keywords) and
                not has_starargs(node)
        ):
            return None

        try:
            return parse_format(node.func.value.s)
        except ValueError:
            return None

    def visit_Call(self, node: ast.Call) -> None:
        parsed = self._parse(node)
        if parsed is not None:
            params = _format_params(node)
            seen: Set[str] = set()
            i = 0
            for _, name, spec, _ in parsed:
                # timid: difficult to rewrite correctly
                if spec is not None and '{' in spec:
                    break
                if name is not None:
                    candidate, _, _ = name.partition('.')
                    # timid: could make the f-string longer
                    if candidate and candidate in seen:
                        break
                    # timid: bracketed
                    elif '[' in name:
                        break
                    seen.add(candidate)

                    key = candidate or str(i)
                    # their .format() call is broken currently
                    if key not in params:
                        break
                    if not candidate:
                        i += 1
            else:
                self.fstrings[ast_to_offset(node)] = node

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if (
                # NT = ...("NT", ...)
                len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name) and
                isinstance(node.value, ast.Call) and
                len(node.value.args) >= 1 and
                isinstance(node.value.args[0], ast.Str) and
                node.targets[0].id == node.value.args[0].s and
                not has_starargs(node.value)
        ):
            if (
                    self._is_attr(
                        node.value.func, {'typing'}, 'NamedTuple',
                    ) and
                    len(node.value.args) == 2 and
                    not node.value.keywords and
                    isinstance(node.value.args[1], (ast.List, ast.Tuple)) and
                    len(node.value.args[1].elts) > 0 and
                    all(
                        isinstance(tup, ast.Tuple) and
                        len(tup.elts) == 2 and
                        isinstance(tup.elts[0], ast.Str) and
                        tup.elts[0].s.isidentifier() and
                        tup.elts[0].s not in KEYWORDS
                        for tup in node.value.args[1].elts
                    )
            ):
                self.named_tuples[ast_to_offset(node)] = node.value
            elif (
                    self._is_attr(
                        node.value.func,
                        {'typing', 'typing_extensions'},
                        'TypedDict',
                    ) and
                    len(node.value.args) == 1 and
                    len(node.value.keywords) > 0
            ):
                self.kw_typed_dicts[ast_to_offset(node)] = node.value
            elif (
                    self._is_attr(
                        node.value.func,
                        {'typing', 'typing_extensions'},
                        'TypedDict',
                    ) and
                    len(node.value.args) == 2 and
                    not node.value.keywords and
                    isinstance(node.value.args[1], ast.Dict) and
                    node.value.args[1].keys and
                    all(
                        isinstance(k, ast.Str) and
                        k.s.isidentifier() and
                        k.s not in KEYWORDS
                        for k in node.value.args[1].keys
                    )
            ):
                self.dict_typed_dicts[ast_to_offset(node)] = node.value

        self.generic_visit(node)


def _unparse(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return ''.join((_unparse(node.value), '.', node.attr))
    elif isinstance(node, ast.Call):
        return '{}()'.format(_unparse(node.func))
    elif isinstance(node, ast.Subscript):
        if sys.version_info >= (3, 9):  # pragma: no cover (py39+)
            node_slice: ast.expr = node.slice
        elif isinstance(node.slice, ast.Index):  # pragma: no cover (<py39)
            node_slice = node.slice.value
        else:
            raise AssertionError(f'expected Slice: {ast.dump(node)}')
        if isinstance(node_slice, ast.Tuple):
            if len(node_slice.elts) == 1:
                slice_s = f'{_unparse(node_slice.elts[0])},'
            else:
                slice_s = ', '.join(_unparse(elt) for elt in node_slice.elts)
        else:
            slice_s = _unparse(node_slice)
        return '{}[{}]'.format(_unparse(node.value), slice_s)
    elif isinstance(node, ast.Str):
        return repr(node.s)
    elif isinstance(node, ast.Ellipsis):
        return '...'
    elif isinstance(node, ast.List):
        return '[{}]'.format(', '.join(_unparse(elt) for elt in node.elts))
    elif isinstance(node, ast.NameConstant):
        return repr(node.value)
    else:
        raise NotImplementedError(ast.dump(node))


def _to_fstring(src: str, call: ast.Call) -> str:
    params = _format_params(call)

    parts = []
    i = 0
    for s, name, spec, conv in parse_format('f' + src):
        if name is not None:
            k, dot, rest = name.partition('.')
            name = ''.join((params[k or str(i)], dot, rest))
            if not k:  # named and auto params can be in different orders
                i += 1
        parts.append((s, name, spec, conv))
    return unparse_parsed_string(parts)


def _replace_typed_class(
        tokens: List[Token],
        i: int,
        call: ast.Call,
        types: Dict[str, ast.expr],
) -> None:
    if i > 0 and tokens[i - 1].name in {'INDENT', UNIMPORTANT_WS}:
        indent = f'{tokens[i - 1].src}{" " * 4}'
    else:
        indent = ' ' * 4

    # NT = NamedTuple("nt", [("a", int)])
    # ^i                                 ^end
    end = i + 1
    while end < len(tokens) and tokens[end].name != 'NEWLINE':
        end += 1

    attrs = '\n'.join(f'{indent}{k}: {_unparse(v)}' for k, v in types.items())
    src = f'class {tokens[i].src}({_unparse(call.func)}):\n{attrs}'
    tokens[i:end] = [Token('CODE', src)]


def _fix_py36_plus(contents_text: str) -> str:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindPy36Plus()
    visitor.visit(ast_obj)

    if not any((
            visitor.fstrings,
            visitor.named_tuples,
            visitor.dict_typed_dicts,
            visitor.kw_typed_dicts,
    )):
        return contents_text

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:  # pragma: no cover (bpo-2180)
        return contents_text
    for i, token in reversed_enumerate(tokens):
        if token.offset in visitor.fstrings:
            node = visitor.fstrings[token.offset]

            # TODO: handle \N escape sequences
            if r'\N' in token.src:
                continue

            paren = i + 3
            if tokens_to_src(tokens[i + 1:paren + 1]) != '.format(':
                continue

            # we don't actually care about arg position, so we pass `node`
            fmt_victims = victims(tokens, paren, node, gen=False)
            end = fmt_victims.ends[-1]
            # if it spans more than one line, bail
            if tokens[end].line != token.line:
                continue

            tokens[i] = token._replace(src=_to_fstring(token.src, node))
            del tokens[i + 1:end + 1]
        elif token.offset in visitor.named_tuples and token.name == 'NAME':
            call = visitor.named_tuples[token.offset]
            types: Dict[str, ast.expr] = {
                tup.elts[0].s: tup.elts[1]  # type: ignore  # (checked above)
                for tup in call.args[1].elts  # type: ignore  # (checked above)
            }
            _replace_typed_class(tokens, i, call, types)
        elif token.offset in visitor.kw_typed_dicts and token.name == 'NAME':
            call = visitor.kw_typed_dicts[token.offset]
            types = {
                arg.arg: arg.value  # type: ignore  # (checked above)
                for arg in call.keywords
            }
            _replace_typed_class(tokens, i, call, types)
        elif token.offset in visitor.dict_typed_dicts and token.name == 'NAME':
            call = visitor.dict_typed_dicts[token.offset]
            types = {
                k.s: v  # type: ignore  # (checked above)
                for k, v in zip(
                    call.args[1].keys,  # type: ignore  # (checked above)
                    call.args[1].values,  # type: ignore  # (checked above)
                )
            }
            _replace_typed_class(tokens, i, call, types)

    return tokens_to_src(tokens)


def _fix_file(filename: str, args: argparse.Namespace) -> int:
    if filename == '-':
        contents_bytes = sys.stdin.buffer.read()
    else:
        with open(filename, 'rb') as fb:
            contents_bytes = fb.read()

    try:
        contents_text_orig = contents_text = contents_bytes.decode()
    except UnicodeDecodeError:
        print(f'{filename} is non-utf-8 (not supported)')
        return 1

    contents_text = _fix_plugins(
        contents_text,
        min_version=args.min_version,
        keep_percent_format=args.keep_percent_format,
    )
    contents_text = _fix_tokens(contents_text, min_version=args.min_version)
    if args.min_version >= (3,):
        contents_text = _fix_py3_plus(
            contents_text, args.min_version, args.keep_mock,
        )
    if args.min_version >= (3, 6):
        contents_text = _fix_py36_plus(contents_text)

    if filename == '-':
        print(contents_text, end='')
    elif contents_text != contents_text_orig:
        print(f'Rewriting {filename}', file=sys.stderr)
        with open(filename, 'w', encoding='UTF-8', newline='') as f:
            f.write(contents_text)

    if args.exit_zero_even_if_changed:
        return 0
    else:
        return contents_text != contents_text_orig


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('--exit-zero-even-if-changed', action='store_true')
    parser.add_argument('--keep-percent-format', action='store_true')
    parser.add_argument('--keep-mock', action='store_true')
    parser.add_argument(
        '--py3-plus', '--py3-only',
        action='store_const', dest='min_version', default=(2, 7), const=(3,),
    )
    parser.add_argument(
        '--py36-plus',
        action='store_const', dest='min_version', const=(3, 6),
    )
    parser.add_argument(
        '--py37-plus',
        action='store_const', dest='min_version', const=(3, 7),
    )
    parser.add_argument(
        '--py38-plus',
        action='store_const', dest='min_version', const=(3, 8),
    )
    parser.add_argument(
        '--py39-plus',
        action='store_const', dest='min_version', const=(3, 9),
    )
    args = parser.parse_args(argv)

    ret = 0
    for filename in args.filenames:
        ret |= _fix_file(filename, args)
    return ret


if __name__ == '__main__':
    exit(main())
