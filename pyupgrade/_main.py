import argparse
import ast
import collections
import re
import string
import sys
import tokenize
from typing import Dict
from typing import List
from typing import Match
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple

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
from pyupgrade._ast_helpers import contains_await
from pyupgrade._ast_helpers import has_starargs
from pyupgrade._data import FUNCS
from pyupgrade._data import Settings
from pyupgrade._data import Version
from pyupgrade._data import visit
from pyupgrade._string_helpers import curly_escape
from pyupgrade._string_helpers import is_ascii
from pyupgrade._string_helpers import is_codec
from pyupgrade._string_helpers import NAMED_UNICODE_RE
from pyupgrade._token_helpers import CLOSING
from pyupgrade._token_helpers import KEYWORDS
from pyupgrade._token_helpers import OPENING
from pyupgrade._token_helpers import parse_call_args
from pyupgrade._token_helpers import remove_brace

DotFormatPart = Tuple[str, Optional[str], Optional[str], Optional[str]]

FUNC_TYPES = (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)

_stdlib_parse_format = string.Formatter().parse


def parse_format(s: str) -> Tuple[DotFormatPart, ...]:
    """handle named escape sequences"""
    ret: List[DotFormatPart] = []

    for part in NAMED_UNICODE_RE.split(s):
        if NAMED_UNICODE_RE.fullmatch(part):
            if not ret:
                ret.append((part, None, None, None))
            else:
                ret[-1] = (ret[-1][0] + part, None, None, None)
        else:
            first = True
            for tup in _stdlib_parse_format(part):
                if not first or not ret:
                    ret.append(tup)
                else:
                    ret[-1] = (ret[-1][0] + tup[0], *tup[1:])
                first = False

    if not ret:
        ret.append((s, None, None, None))

    return tuple(ret)


def unparse_parsed_string(parsed: Sequence[DotFormatPart]) -> str:
    def _convert_tup(tup: DotFormatPart) -> str:
        ret, field_name, format_spec, conversion = tup
        ret = curly_escape(ret)
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


def _fix_plugins(contents_text: str, settings: Settings) -> str:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    callbacks = visit(FUNCS, ast_obj, settings)

    if not callbacks:
        return contents_text

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:  # pragma: no cover (bpo-2180)
        return contents_text

    _fixup_dedent_tokens(tokens)

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
    parts = rfind_string_parts(tokens, i - 2)
    if not parts:
        return

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
        if is_codec(encoding, 'ascii') or is_codec(encoding, 'utf-8'):
            latin1_ok = False
        elif is_codec(encoding, 'iso8859-1'):
            latin1_ok = True
        else:
            return
    else:
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
        ((3, 10), ()),
        ((3, 11), ()),
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


def _format_params(call: ast.Call) -> Set[str]:
    params = {str(i) for i, arg in enumerate(call.args)}
    for kwd in call.keywords:
        # kwd.arg can't be None here because we exclude starargs
        assert kwd.arg is not None
        params.add(kwd.arg)
    return params


class FindPy36Plus(ast.NodeVisitor):
    def __init__(self, *, min_version: Version) -> None:
        self.fstrings: Dict[Offset, ast.Call] = {}
        self.named_tuples: Dict[Offset, ast.Call] = {}
        self.dict_typed_dicts: Dict[Offset, ast.Call] = {}
        self.kw_typed_dicts: Dict[Offset, ast.Call] = {}
        self._from_imports: Dict[str, Set[str]] = collections.defaultdict(set)
        self.min_version = min_version

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
                if self.min_version >= (3, 7) or not contains_await(node):
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
                    len(node.value.keywords) > 0 and
                    not any(
                        keyword.arg == 'total'
                        for keyword in node.value.keywords
                    )
            ):
                self.kw_typed_dicts[ast_to_offset(node)] = node.value
            elif (
                    self._is_attr(
                        node.value.func,
                        {'typing', 'typing_extensions'},
                        'TypedDict',
                    ) and
                    len(node.value.args) == 2 and
                    (
                        not node.value.keywords or
                        (
                            len(node.value.keywords) == 1 and
                            node.value.keywords[0].arg == 'total' and
                            isinstance(
                                node.value.keywords[0].value,
                                (ast.Constant, ast.NameConstant),
                            )
                        )
                    ) and
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
    elif isinstance(node, ast.Subscript):
        if sys.version_info >= (3, 9):  # pragma: >=3.9 cover
            node_slice: ast.expr = node.slice
        elif isinstance(node.slice, ast.Index):  # pragma: <3.9 cover
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
        return f'{_unparse(node.value)}[{slice_s}]'
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


def _skip_unimportant_ws(tokens: List[Token], i: int) -> int:
    while tokens[i].name == 'UNIMPORTANT_WS':
        i += 1
    return i


def _to_fstring(
    src: str, tokens: List[Token], args: List[Tuple[int, int]],
) -> str:
    params = {}
    i = 0
    for start, end in args:
        start = _skip_unimportant_ws(tokens, start)
        if tokens[start].name == 'NAME':
            after = _skip_unimportant_ws(tokens, start + 1)
            if tokens[after].src == '=':  # keyword argument
                params[tokens[start].src] = tokens_to_src(
                    tokens[after + 1:end],
                ).strip()
                continue
        params[str(i)] = tokens_to_src(tokens[start:end]).strip()
        i += 1

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


def _typed_class_replacement(
        tokens: List[Token],
        i: int,
        call: ast.Call,
        types: Dict[str, ast.expr],
) -> Tuple[int, str]:
    while i > 0 and tokens[i - 1].name == 'DEDENT':
        i -= 1
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
    return end, attrs


def _fix_py36_plus(contents_text: str, *, min_version: Version) -> str:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindPy36Plus(min_version=min_version)
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
            paren = i + 3
            if tokens_to_src(tokens[i + 1:paren + 1]) != '.format(':
                continue

            args, end = parse_call_args(tokens, paren)
            # if it spans more than one line, bail
            if tokens[end - 1].line != token.line:
                continue

            args_src = tokens_to_src(tokens[paren:end])
            if '\\' in args_src or '"' in args_src or "'" in args_src:
                continue

            tokens[i] = token._replace(
                src=_to_fstring(token.src, tokens, args),
            )
            del tokens[i + 1:end]
        elif token.offset in visitor.named_tuples and token.name == 'NAME':
            call = visitor.named_tuples[token.offset]
            types: Dict[str, ast.expr] = {
                tup.elts[0].s: tup.elts[1]
                for tup in call.args[1].elts  # type: ignore  # (checked above)
            }
            end, attrs = _typed_class_replacement(tokens, i, call, types)
            src = f'class {tokens[i].src}({_unparse(call.func)}):\n{attrs}'
            tokens[i:end] = [Token('CODE', src)]
        elif token.offset in visitor.kw_typed_dicts and token.name == 'NAME':
            call = visitor.kw_typed_dicts[token.offset]
            types = {
                arg.arg: arg.value  # type: ignore  # (checked above)
                for arg in call.keywords
            }
            end, attrs = _typed_class_replacement(tokens, i, call, types)
            src = f'class {tokens[i].src}({_unparse(call.func)}):\n{attrs}'
            tokens[i:end] = [Token('CODE', src)]
        elif token.offset in visitor.dict_typed_dicts and token.name == 'NAME':
            call = visitor.dict_typed_dicts[token.offset]
            types = {
                k.s: v
                for k, v in zip(
                    call.args[1].keys,  # type: ignore  # (checked above)
                    call.args[1].values,  # type: ignore  # (checked above)
                )
            }
            if call.keywords:
                total = call.keywords[0].value.value  # type: ignore # (checked above)  # noqa: E501
                end, attrs = _typed_class_replacement(tokens, i, call, types)
                src = (
                    f'class {tokens[i].src}('
                    f'{_unparse(call.func)}, total={total}'
                    f'):\n'
                    f'{attrs}'
                )
                tokens[i:end] = [Token('CODE', src)]
            else:
                end, attrs = _typed_class_replacement(tokens, i, call, types)
                src = f'class {tokens[i].src}({_unparse(call.func)}):\n{attrs}'
                tokens[i:end] = [Token('CODE', src)]

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
        settings=Settings(
            min_version=args.min_version,
            keep_percent_format=args.keep_percent_format,
            keep_mock=args.keep_mock,
            keep_runtime_typing=args.keep_runtime_typing,
        ),
    )
    contents_text = _fix_tokens(contents_text, min_version=args.min_version)
    if args.min_version >= (3, 6):
        contents_text = _fix_py36_plus(
            contents_text, min_version=args.min_version,
        )

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
    parser.add_argument('--keep-runtime-typing', action='store_true')
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
    parser.add_argument(
        '--py310-plus',
        action='store_const', dest='min_version', const=(3, 10),
    )
    parser.add_argument(
        '--py311-plus',
        action='store_const', dest='min_version', const=(3, 11),
    )
    args = parser.parse_args(argv)

    ret = 0
    for filename in args.filenames:
        ret |= _fix_file(filename, args)
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
