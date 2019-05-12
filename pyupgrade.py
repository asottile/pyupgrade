from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import ast
import collections
import io
import keyword
import re
import string
import sys
import tokenize
import warnings

from tokenize_rt import ESCAPED_NL
from tokenize_rt import Offset
from tokenize_rt import reversed_enumerate
from tokenize_rt import src_to_tokens
from tokenize_rt import Token
from tokenize_rt import tokens_to_src
from tokenize_rt import UNIMPORTANT_WS


_stdlib_parse_format = string.Formatter().parse


def parse_format(s):
    """Makes the empty string not a special case.  In the stdlib, there's
    loss of information (the type) on the empty string.
    """
    parsed = tuple(_stdlib_parse_format(s))
    if not parsed:
        return ((s, None, None, None),)
    else:
        return parsed


def unparse_parsed_string(parsed):
    stype = type(parsed[0][0])
    j = stype()

    def _convert_tup(tup):
        ret, field_name, format_spec, conversion = tup
        ret = ret.replace(stype('{'), stype('{{'))
        ret = ret.replace(stype('}'), stype('}}'))
        if field_name is not None:
            ret += stype('{') + field_name
            if conversion:
                ret += stype('!') + conversion
            if format_spec:
                ret += stype(':') + format_spec
            ret += stype('}')
        return ret

    return j.join(_convert_tup(tup) for tup in parsed)


NON_CODING_TOKENS = frozenset(('COMMENT', ESCAPED_NL, 'NL', UNIMPORTANT_WS))


def _ast_to_offset(node):
    return Offset(node.lineno, node.col_offset)


def ast_parse(contents_text):
    # intentionally ignore warnings, we might be fixing warning-ridden syntax
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return ast.parse(contents_text.encode('UTF-8'))


def inty(s):
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def _rewrite_string_literal(literal):
    try:
        parsed_fmt = parse_format(literal)
    except ValueError:
        # Well, the format literal was malformed, so skip it
        return literal

    last_int = -1
    # The last segment will always be the end of the string and not a format
    # We slice it off here to avoid a "None" format key
    for _, fmtkey, spec, _ in parsed_fmt[:-1]:
        if inty(fmtkey) and int(fmtkey) == last_int + 1 and '{' not in spec:
            last_int += 1
        else:
            return literal

    def _remove_fmt(tup):
        if tup[1] is None:
            return tup
        else:
            return (tup[0], '', tup[2], tup[3])

    removed = [_remove_fmt(tup) for tup in parsed_fmt]
    return unparse_parsed_string(removed)


def _fix_format_literals(contents_text):
    tokens = src_to_tokens(contents_text)

    to_replace = []
    string_start = None
    string_end = None
    seen_dot = False

    for i, token in enumerate(tokens):
        if string_start is None and token.name == 'STRING':
            string_start = i
            string_end = i + 1
        elif string_start is not None and token.name == 'STRING':
            string_end = i + 1
        elif string_start is not None and token.src == '.':
            seen_dot = True
        elif seen_dot and token.src == 'format':
            to_replace.append((string_start, string_end))
            string_start, string_end, seen_dot = None, None, False
        elif token.name not in NON_CODING_TOKENS:
            string_start, string_end, seen_dot = None, None, False

    for start, end in reversed(to_replace):
        src = tokens_to_src(tokens[start:end])
        new_src = _rewrite_string_literal(src)
        tokens[start:end] = [Token('STRING', new_src)]

    return tokens_to_src(tokens)


def _has_kwargs(call):
    return bool(call.keywords) or bool(getattr(call, 'kwargs', None))


BRACES = {'(': ')', '[': ']', '{': '}'}
OPENING, CLOSING = frozenset(BRACES), frozenset(BRACES.values())
SET_TRANSFORM = (ast.List, ast.ListComp, ast.GeneratorExp, ast.Tuple)


def _is_wtf(func, tokens, i):
    return tokens[i].src != func or tokens[i + 1].src != '('


def _process_set_empty_literal(tokens, start):
    if _is_wtf('set', tokens, start):
        return

    i = start + 2
    brace_stack = ['(']
    while brace_stack:
        token = tokens[i].src
        if token == BRACES[brace_stack[-1]]:
            brace_stack.pop()
        elif token in BRACES:
            brace_stack.append(token)
        elif '\n' in token:
            # Contains a newline, could cause a SyntaxError, bail
            return
        i += 1

    # Remove the inner tokens
    del tokens[start + 2:i - 1]


def _search_until(tokens, idx, arg):
    while (
            idx < len(tokens) and
            not (
                tokens[idx].line == arg.lineno and
                tokens[idx].utf8_byte_offset == arg.col_offset
            )
    ):
        idx += 1
    return idx


if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    # python 3.8 fixed the offsets of generators / tuples
    def _arg_token_index(tokens, i, arg):
        idx = _search_until(tokens, i, arg) + 1
        while idx < len(tokens) and tokens[idx].name in NON_CODING_TOKENS:
            idx += 1
        return idx
else:  # pragma: no cover (<py38)
    def _arg_token_index(tokens, i, arg):
        # lists containing non-tuples report the first element correctly
        if isinstance(arg, ast.List):
            # If the first element is a tuple, the ast lies to us about its col
            # offset.  We must find the first `(` token after the start of the
            # list element.
            if isinstance(arg.elts[0], ast.Tuple):
                i = _search_until(tokens, i, arg)
                return _find_open_paren(tokens, i)
            else:
                return _search_until(tokens, i, arg.elts[0])
            # others' start position points at their first child node already
        else:
            return _search_until(tokens, i, arg)


Victims = collections.namedtuple(
    'Victims', ('starts', 'ends', 'first_comma_index', 'arg_index'),
)


def _victims(tokens, start, arg, gen):
    starts = [start]
    start_depths = [1]
    ends = []
    first_comma_index = None
    arg_depth = None
    arg_index = _arg_token_index(tokens, start, arg)
    brace_stack = [tokens[start].src]
    i = start + 1

    while brace_stack:
        token = tokens[i].src
        is_start_brace = token in BRACES
        is_end_brace = token == BRACES[brace_stack[-1]]

        if i == arg_index:
            arg_depth = len(brace_stack)

        if is_start_brace:
            brace_stack.append(token)

        # Remove all braces before the first element of the inner
        # comprehension's target.
        if is_start_brace and arg_depth is None:
            start_depths.append(len(brace_stack))
            starts.append(i)

        if (
                token == ',' and
                len(brace_stack) == arg_depth and
                first_comma_index is None
        ):
            first_comma_index = i

        if is_end_brace and len(brace_stack) in start_depths:
            if tokens[i - 2].src == ',' and tokens[i - 1].src == ' ':
                ends.extend((i - 2, i - 1, i))
            elif tokens[i - 1].src == ',':
                ends.extend((i - 1, i))
            else:
                ends.append(i)

        if is_end_brace:
            brace_stack.pop()

        i += 1

    # May need to remove a trailing comma for a comprehension
    if gen:
        i -= 2
        while tokens[i].name in NON_CODING_TOKENS:
            i -= 1
        if tokens[i].src == ',':
            ends = sorted(set(ends + [i]))

    return Victims(starts, ends, first_comma_index, arg_index)


def _find_open_paren(tokens, i):
    while tokens[i].src != '(':
        i += 1
    return i


def _is_on_a_line_by_self(tokens, i):
    return (
        tokens[i - 2].name == 'NL' and
        tokens[i - 1].name == UNIMPORTANT_WS and
        tokens[i - 1].src.isspace() and
        tokens[i + 1].name == 'NL'
    )


def _remove_brace(tokens, i):
    if _is_on_a_line_by_self(tokens, i):
        del tokens[i - 1:i + 2]
    else:
        del tokens[i]


def _process_set_literal(tokens, start, arg):
    if _is_wtf('set', tokens, start):
        return

    gen = isinstance(arg, ast.GeneratorExp)
    set_victims = _victims(tokens, start + 1, arg, gen=gen)

    del set_victims.starts[0]
    end_index = set_victims.ends.pop()

    tokens[end_index] = Token('OP', '}')
    for index in reversed(set_victims.starts + set_victims.ends):
        _remove_brace(tokens, index)
    tokens[start:start + 2] = [Token('OP', '{')]


def _process_dict_comp(tokens, start, arg):
    if _is_wtf('dict', tokens, start):
        return

    dict_victims = _victims(tokens, start + 1, arg, gen=True)
    elt_victims = _victims(tokens, dict_victims.arg_index, arg.elt, gen=True)

    del dict_victims.starts[0]
    end_index = dict_victims.ends.pop()

    tokens[end_index] = Token('OP', '}')
    for index in reversed(dict_victims.ends):
        _remove_brace(tokens, index)
    # See #6, Fix SyntaxError from rewriting dict((a, b)for a, b in y)
    if tokens[elt_victims.ends[-1] + 1].src == 'for':
        tokens.insert(elt_victims.ends[-1] + 1, Token(UNIMPORTANT_WS, ' '))
    for index in reversed(elt_victims.ends):
        _remove_brace(tokens, index)
    tokens[elt_victims.first_comma_index] = Token('OP', ':')
    for index in reversed(dict_victims.starts + elt_victims.starts):
        _remove_brace(tokens, index)
    tokens[start:start + 2] = [Token('OP', '{')]


def _process_is_literal(tokens, i, compare):
    while tokens[i].src != 'is':
        i -= 1
    if isinstance(compare, ast.Is):
        tokens[i] = tokens[i]._replace(src='==')
    else:
        tokens[i] = tokens[i]._replace(src='!=')
        # since we iterate backward, the dummy tokens keep the same length
        i += 1
        while tokens[i].src != 'not':
            tokens[i] = Token('DUMMY', '')
            i += 1
        tokens[i] = Token('DUMMY', '')


LITERAL_TYPES = (ast.Str, ast.Num)
if sys.version_info >= (3,):  # pragma: no cover (py3+)
    LITERAL_TYPES += (ast.Bytes,)


class Py2CompatibleVisitor(ast.NodeVisitor):
    def __init__(self):  # type: () -> None
        self.dicts = {}
        self.sets = {}
        self.set_empty_literals = {}
        self.is_literal = {}

    def visit_Call(self, node):  # type: (ast.Call) -> None
        if (
                isinstance(node.func, ast.Name) and
                node.func.id == 'set' and
                len(node.args) == 1 and
                not _has_kwargs(node) and
                isinstance(node.args[0], SET_TRANSFORM)
        ):
            arg, = node.args
            key = _ast_to_offset(node.func)
            if isinstance(arg, (ast.List, ast.Tuple)) and not arg.elts:
                self.set_empty_literals[key] = arg
            else:
                self.sets[key] = arg
        elif (
                isinstance(node.func, ast.Name) and
                node.func.id == 'dict' and
                len(node.args) == 1 and
                not _has_kwargs(node) and
                isinstance(node.args[0], (ast.ListComp, ast.GeneratorExp)) and
                isinstance(node.args[0].elt, (ast.Tuple, ast.List)) and
                len(node.args[0].elt.elts) == 2
        ):
            arg, = node.args
            self.dicts[_ast_to_offset(node.func)] = arg
        self.generic_visit(node)

    def visit_Compare(self, node):  # type: (ast.Compare) -> None
        left = node.left
        for op, right in zip(node.ops, node.comparators):
            if (
                    isinstance(op, (ast.Is, ast.IsNot)) and
                    (
                        isinstance(left, LITERAL_TYPES) or
                        isinstance(right, LITERAL_TYPES)
                    )
            ):
                self.is_literal[_ast_to_offset(right)] = op
            left = right

        self.generic_visit(node)


def _fix_py2_compatible(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text
    visitor = Py2CompatibleVisitor()
    visitor.visit(ast_obj)
    if not any((
            visitor.dicts,
            visitor.sets,
            visitor.set_empty_literals,
            visitor.is_literal,
    )):
        return contents_text

    tokens = src_to_tokens(contents_text)
    for i, token in reversed_enumerate(tokens):
        if token.offset in visitor.dicts:
            _process_dict_comp(tokens, i, visitor.dicts[token.offset])
        elif token.offset in visitor.set_empty_literals:
            _process_set_empty_literal(tokens, i)
        elif token.offset in visitor.sets:
            _process_set_literal(tokens, i, visitor.sets[token.offset])
        elif token.offset in visitor.is_literal:
            _process_is_literal(tokens, i, visitor.is_literal[token.offset])
    return tokens_to_src(tokens)


def _imports_unicode_literals(contents_text):
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
                node.module == '__future__' and
                any(name.name == 'unicode_literals' for name in node.names)
            ):
                return True
            elif node.module == '__future__':
                continue
            else:
                return False
        else:
            return False


STRING_PREFIXES_RE = re.compile('^([^\'"]*)(.*)$', re.DOTALL)
# https://docs.python.org/3/reference/lexical_analysis.html
ESCAPE_STARTS = frozenset((
    '\n', '\r', '\\', "'", '"', 'a', 'b', 'f', 'n', 'r', 't', 'v',
    '0', '1', '2', '3', '4', '5', '6', '7',  # octal escapes
    'x',  # hex escapes
))
ESCAPE_RE = re.compile(r'\\.', re.DOTALL)
NAMED_ESCAPE_NAME = re.compile(r'\{[^}]+\}')


def _parse_string_literal(s):
    match = STRING_PREFIXES_RE.match(s)
    return match.group(1), match.group(2)


def _fix_escape_sequences(token):
    prefix, rest = _parse_string_literal(token.src)
    actual_prefix = prefix.lower()

    if 'r' in actual_prefix or '\\' not in rest:
        return token

    is_bytestring = 'b' in actual_prefix

    def _is_valid_escape(match):
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

    def cb(match):
        matched = match.group()
        if _is_valid_escape(match):
            return matched
        else:
            return r'\{}'.format(matched)

    if has_invalid_escapes and (has_valid_escapes or 'u' in actual_prefix):
        return token._replace(src=prefix + ESCAPE_RE.sub(cb, rest))
    elif has_invalid_escapes and not has_valid_escapes:
        return token._replace(src=prefix + 'r' + rest)
    else:
        return token


def _remove_u_prefix(token):
    prefix, rest = _parse_string_literal(token.src)
    if 'u' not in prefix.lower():
        return token
    else:
        new_prefix = prefix.replace('u', '').replace('U', '')
        return Token('STRING', new_prefix + rest)


def _fix_ur_literals(token):
    prefix, rest = _parse_string_literal(token.src)
    if prefix.lower() != 'ur':
        return token
    else:
        def cb(match):
            escape = match.group()
            if escape[1].lower() == 'u':
                return escape
            else:
                return '\\' + match.group()

        rest = ESCAPE_RE.sub(cb, rest)
        prefix = prefix.replace('r', '').replace('R', '')
        return token._replace(src=prefix + rest)


def _fix_long(src):
    return src.rstrip('lL')


def _fix_octal(s):
    if not s.startswith('0') or not s.isdigit() or s == len(s) * '0':
        return s
    elif len(s) == 2:  # pragma: no cover (py2 only)
        return s[1:]
    else:  # pragma: no cover (py2 only)
        return '0o' + s[1:]


def _is_string_prefix(token):
    return token.name == 'NAME' and set(token.src.lower()) <= set('bfru')


def _fix_extraneous_parens(tokens, i):
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
        _remove_brace(tokens, end)
        _remove_brace(tokens, start)


def _fix_tokens(contents_text, py3_plus):
    remove_u_prefix = py3_plus or _imports_unicode_literals(contents_text)

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:
        return contents_text
    for i, token in reversed_enumerate(tokens):
        if token.name == 'NUMBER':
            tokens[i] = token._replace(src=_fix_long(_fix_octal(token.src)))
        elif token.name == 'STRING':
            # when a string prefix is not recognized, the tokenizer produces a
            # NAME token followed by a STRING token
            if i > 0 and _is_string_prefix(tokens[i - 1]):
                tokens[i] = token._replace(src=tokens[i - 1].src + token.src)
                tokens[i - 1] = tokens[i - 1]._replace(src='')

            tokens[i] = _fix_ur_literals(tokens[i])
            if remove_u_prefix:
                tokens[i] = _remove_u_prefix(tokens[i])
            tokens[i] = _fix_escape_sequences(tokens[i])
        elif token.src == '(':
            _fix_extraneous_parens(tokens, i)
    return tokens_to_src(tokens)


MAPPING_KEY_RE = re.compile(r'\(([^()]*)\)')
CONVERSION_FLAG_RE = re.compile('[#0+ -]*')
WIDTH_RE = re.compile(r'(?:\*|\d*)')
PRECISION_RE = re.compile(r'(?:\.(?:\*|\d*))?')
LENGTH_RE = re.compile('[hlL]?')


def parse_percent_format(s):
    def _parse_inner():
        string_start = 0
        string_end = 0
        in_fmt = False

        i = 0
        while i < len(s):
            if not in_fmt:
                try:
                    i = s.index('%', i)
                except ValueError:  # no more % fields!
                    yield s[string_start:], None
                    return
                else:
                    string_end = i
                    i += 1
                    in_fmt = True
            else:
                key_match = MAPPING_KEY_RE.match(s, i)
                if key_match:
                    key = key_match.group(1)
                    i = key_match.end()
                else:
                    key = None

                conversion_flag_match = CONVERSION_FLAG_RE.match(s, i)
                conversion_flag = conversion_flag_match.group() or None
                i = conversion_flag_match.end()

                width_match = WIDTH_RE.match(s, i)
                width = width_match.group() or None
                i = width_match.end()

                precision_match = PRECISION_RE.match(s, i)
                precision = precision_match.group() or None
                i = precision_match.end()

                # length modifier is ignored
                i = LENGTH_RE.match(s, i).end()

                conversion = s[i]
                i += 1

                fmt = (key, conversion_flag, width, precision, conversion)
                yield s[string_start:string_end], fmt

                in_fmt = False
                string_start = i

    return tuple(_parse_inner())


class FindPercentFormats(ast.NodeVisitor):
    def __init__(self):
        self.found = {}

    def visit_BinOp(self, node):  # type: (ast.BinOp) -> None
        if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Str):
            for _, fmt in parse_percent_format(node.left.s):
                if not fmt:
                    continue
                key, conversion_flag, width, precision, conversion = fmt
                # timid: these require out-of-order parameter consumption
                if width == '*' or precision == '.*':
                    break
                # timid: these conversions require modification of parameters
                if conversion in {'d', 'i', 'u', 'c'}:
                    break
                # timid: py2: %#o formats different from {:#o} (TODO: --py3)
                if '#' in (conversion_flag or '') and conversion == 'o':
                    break
                # timid: no equivalent in format
                if key == '':
                    break
                # timid: py2: conversion is subject to modifiers (TODO: --py3)
                nontrivial_fmt = any((conversion_flag, width, precision))
                if conversion == '%' and nontrivial_fmt:
                    break
                # timid: no equivalent in format
                if conversion in {'a', 'r'} and nontrivial_fmt:
                    break
                # all dict substitutions must be named
                if isinstance(node.right, ast.Dict) and not key:
                    break
            else:
                self.found[_ast_to_offset(node)] = node
        self.generic_visit(node)


def _simplify_conversion_flag(flag):
    parts = []
    for c in flag:
        if c in parts:
            continue
        c = c.replace('-', '<')
        parts.append(c)
        if c == '<' and '0' in parts:
            parts.remove('0')
        elif c == '+' and ' ' in parts:
            parts.remove(' ')
    return ''.join(parts)


def _percent_to_format(s):
    def _handle_part(part):
        s, fmt = part
        s = s.replace('{', '{{').replace('}', '}}')
        if fmt is None:
            return s
        else:
            key, conversion_flag, width, precision, conversion = fmt
            if conversion == '%':
                return s + '%'
            parts = [s, '{']
            if width and conversion == 's' and not conversion_flag:
                conversion_flag = '>'
            if conversion == 's':
                conversion = None
            if key:
                parts.append(key)
            if conversion in {'r', 'a'}:
                converter = '!{}'.format(conversion)
                conversion = ''
            else:
                converter = ''
            if any((conversion_flag, width, precision, conversion)):
                parts.append(':')
            if conversion_flag:
                parts.append(_simplify_conversion_flag(conversion_flag))
            parts.extend(x for x in (width, precision, conversion) if x)
            parts.extend(converter)
            parts.append('}')
            return ''.join(parts)

    return ''.join(_handle_part(part) for part in parse_percent_format(s))


def _is_bytestring(s):
    for c in s:
        if c in '"\'':
            return False
        elif c.lower() == 'b':
            return True
    else:
        return False


def _is_ascii(s):
    if sys.version_info >= (3, 7):  # pragma: no cover (py37+)
        return s.isascii()
    else:  # pragma: no cover (<py37)
        return all(c in string.printable for c in s)


def _fix_percent_format_tuple(tokens, start, node):
    # TODO: this is overly timid
    paren = start + 4
    if tokens_to_src(tokens[start + 1:paren + 1]) != ' % (':
        return

    victims = _victims(tokens, paren, node.right, gen=False)
    victims.ends.pop()

    for index in reversed(victims.starts + victims.ends):
        _remove_brace(tokens, index)

    newsrc = _percent_to_format(tokens[start].src)
    tokens[start] = tokens[start]._replace(src=newsrc)
    tokens[start + 1:paren] = [Token('Format', '.format'), Token('OP', '(')]


IDENT_RE = re.compile('^[a-zA-Z_][a-zA-Z0-9_]*$')


def _fix_percent_format_dict(tokens, start, node):
    seen_keys = set()
    keys = {}
    for k in node.right.keys:
        # not a string key
        if not isinstance(k, ast.Str):
            return
        # duplicate key
        elif k.s in seen_keys:
            return
        # not an identifier
        elif not IDENT_RE.match(k.s):
            return
        # a keyword
        elif k.s in keyword.kwlist:
            return
        seen_keys.add(k.s)
        keys[_ast_to_offset(k)] = k

    # TODO: this is overly timid
    brace = start + 4
    if tokens_to_src(tokens[start + 1:brace + 1]) != ' % {':
        return

    victims = _victims(tokens, brace, node.right, gen=False)
    brace_end = victims.ends[-1]

    key_indices = []
    for i, token in enumerate(tokens[brace:brace_end], brace):
        k = keys.pop(token.offset, None)
        if k is None:
            continue
        # we found the key, but the string didn't match (implicit join?)
        elif ast.literal_eval(token.src) != k.s:
            return
        # the map uses some strange syntax that's not `'k': v`
        elif tokens_to_src(tokens[i + 1:i + 3]) != ': ':
            return
        else:
            key_indices.append((i, k.s))
    assert not keys, keys

    tokens[brace_end] = tokens[brace_end]._replace(src=')')
    for (key_index, s) in reversed(key_indices):
        tokens[key_index:key_index + 3] = [Token('CODE', '{}='.format(s))]
    newsrc = _percent_to_format(tokens[start].src)
    tokens[start] = tokens[start]._replace(src=newsrc)
    tokens[start + 1:brace + 1] = [Token('CODE', '.format'), Token('OP', '(')]


def _fix_percent_format(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindPercentFormats()
    visitor.visit(ast_obj)

    if not visitor.found:
        return contents_text

    tokens = src_to_tokens(contents_text)

    for i, token in reversed_enumerate(tokens):
        node = visitor.found.get(token.offset)
        if node is None:
            continue

        # no .format() equivalent for bytestrings in py3
        # note that this code is only necessary when running in python2
        if _is_bytestring(tokens[i].src):  # pragma: no cover (py2-only)
            continue

        if isinstance(node.right, ast.Tuple):
            _fix_percent_format_tuple(tokens, i, node)
        elif isinstance(node.right, ast.Dict):
            _fix_percent_format_dict(tokens, i, node)

    return tokens_to_src(tokens)


# PY2: arguments are `Name`, PY3: arguments are `arg`
ARGATTR = 'id' if str is bytes else 'arg'


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
    'get_unbound_method': '{args[0]}',
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
SIX_B_TMPL = 'b{args[0]}'
WITH_METACLASS_NO_BASES_TMPL = 'metaclass={args[0]}'
WITH_METACLASS_BASES_TMPL = '{rest}, metaclass={args[0]}'
SIX_RAISES = {
    'raise_from': 'raise {args[0]} from {rest}',
    'reraise': 'raise {args[1]}.with_traceback({args[2]})',
}


class FindPy3Plus(ast.NodeVisitor):
    class ClassInfo:
        def __init__(self, name):
            self.name = name
            self.def_depth = 0
            self.first_arg_name = ''

    def __init__(self):
        self.bases_to_remove = set()

        self.native_literals = set()

        self._six_from_imports = set()
        self.six_b = set()
        self.six_calls = {}
        self._previous_node = None
        self.six_raises = {}
        self.six_remove_decorators = set()
        self.six_simple = {}
        self.six_type_ctx = {}
        self.six_with_metaclass = set()

        self._class_info_stack = []
        self._in_comp = 0
        self.super_calls = {}

    def _is_six(self, node, names):
        return (
            isinstance(node, ast.Name) and
            node.id in names and
            node.id in self._six_from_imports
        ) or (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            node.value.id == 'six' and
            node.attr in names
        )

    def visit_ImportFrom(self, node):  # type: (ast.ImportFrom) -> None
        if node.module == 'six':
            for name in node.names:
                if not name.asname:
                    self._six_from_imports.add(name.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):  # type: (ast.ClassDef) -> None
        for decorator in node.decorator_list:
            if self._is_six(decorator, ('python_2_unicode_compatible',)):
                self.six_remove_decorators.add(_ast_to_offset(decorator))

        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'object':
                self.bases_to_remove.add(_ast_to_offset(base))
            elif self._is_six(base, ('Iterator',)):
                self.bases_to_remove.add(_ast_to_offset(base))

        if (
                len(node.bases) == 1 and
                isinstance(node.bases[0], ast.Call) and
                self._is_six(node.bases[0].func, ('with_metaclass',))
        ):
            self.six_with_metaclass.add(_ast_to_offset(node.bases[0]))

        self._class_info_stack.append(FindPy3Plus.ClassInfo(node.name))
        self.generic_visit(node)
        self._class_info_stack.pop()

    def _visit_func(self, node):
        if self._class_info_stack:
            class_info = self._class_info_stack[-1]
            class_info.def_depth += 1
            if class_info.def_depth == 1 and node.args.args:
                class_info.first_arg_name = getattr(node.args.args[0], ARGATTR)
            self.generic_visit(node)
            class_info.def_depth -= 1
        else:
            self.generic_visit(node)

    visit_FunctionDef = visit_Lambda = _visit_func

    def _visit_comp(self, node):
        self._in_comp += 1
        self.generic_visit(node)
        self._in_comp -= 1

    visit_ListComp = visit_SetComp = _visit_comp
    visit_DictComp = visit_GeneratorExp = _visit_comp

    def _visit_simple(self, node):
        if self._is_six(node, SIX_SIMPLE_ATTRS):
            self.six_simple[_ast_to_offset(node)] = node
        self.generic_visit(node)

    visit_Name = visit_Attribute = _visit_simple

    def visit_Call(self, node):  # type: (ast.Call) -> None
        if (
                isinstance(node.func, ast.Name) and
                node.func.id in {'isinstance', 'issubclass'} and
                len(node.args) == 2 and
                self._is_six(node.args[1], SIX_TYPE_CTX_ATTRS)
        ):
            self.six_type_ctx[_ast_to_offset(node.args[1])] = node.args[1]
        elif self._is_six(node.func, ('b',)):
            self.six_b.add(_ast_to_offset(node))
        elif self._is_six(node.func, SIX_CALLS):
            self.six_calls[_ast_to_offset(node)] = node
        elif (
                isinstance(self._previous_node, ast.Expr) and
                self._is_six(node.func, SIX_RAISES)
        ):
            self.six_raises[_ast_to_offset(node)] = node
        elif (
                not self._in_comp and
                self._class_info_stack and
                self._class_info_stack[-1].def_depth == 1 and
                isinstance(node.func, ast.Name) and
                node.func.id == 'super' and
                len(node.args) == 2 and
                all(isinstance(arg, ast.Name) for arg in node.args) and
                node.args[0].id == self._class_info_stack[-1].name and
                node.args[1].id == self._class_info_stack[-1].first_arg_name
        ):
            self.super_calls[_ast_to_offset(node)] = node
        elif (
                isinstance(node.func, ast.Name) and
                node.func.id == 'str' and
                len(node.args) == 1 and
                isinstance(node.args[0], ast.Str) and
                not node.keywords and
                not _starargs(node)
        ):
            self.native_literals.add(_ast_to_offset(node))

        self.generic_visit(node)

    def generic_visit(self, node):
        self._previous_node = node
        super(FindPy3Plus, self).generic_visit(node)


def _remove_base_class(tokens, i):
    # look forward and backward to find commas / parens
    brace_stack = []
    j = i
    while tokens[j].src not in {',', ':'}:
        if tokens[j].src == ')':
            brace_stack.append(j)
        j += 1
    right = j

    if tokens[right].src == ':':
        brace_stack.pop()
    else:
        # if there's a close-paren after a trailing comma
        j = right + 1
        while tokens[j].name in NON_CODING_TOKENS:
            j += 1
        if tokens[j].src == ')':
            while tokens[j].src != ':':
                j += 1
            right = j

    if brace_stack:
        last_part = brace_stack[-1]
    else:
        last_part = i

    j = i
    while brace_stack:
        if tokens[j].src == '(':
            brace_stack.pop()
        j -= 1

    while tokens[j].src not in {',', '('}:
        j -= 1
    left = j

    # single base, remove the entire bases
    if tokens[left].src == '(' and tokens[right].src == ':':
        del tokens[left:right]
    # multiple bases, base is first
    elif tokens[left].src == '(' and tokens[right].src != ':':
        # if there's space / comment afterwards remove that too
        while tokens[right + 1].name in {UNIMPORTANT_WS, 'COMMENT'}:
            right += 1
        del tokens[left + 1:right + 1]
    # multiple bases, base is not first
    else:
        del tokens[left:last_part + 1]


def _parse_call_args(tokens, i):
    args = []
    stack = [i]
    i += 1
    arg_start = i

    while stack:
        token = tokens[i]

        if len(stack) == 1 and token.src == ',':
            args.append((arg_start, i))
            arg_start = i + 1
        elif token.src in BRACES:
            stack.append(i)
        elif token.src == BRACES[tokens[stack[-1]].src]:
            stack.pop()
            # if we're at the end, append that argument
            if not stack and tokens_to_src(tokens[arg_start:i]).strip():
                args.append((arg_start, i))

        i += 1

    return args, i


def _get_tmpl(mapping, node):
    if isinstance(node, ast.Name):
        return mapping[node.id]
    else:
        return mapping[node.attr]


def _replace_call(tokens, start, end, args, tmpl):
    arg_strs = [tokens_to_src(tokens[slice(*arg)]).strip() for arg in args]

    start_rest = args[0][1] + 1
    while (
            start_rest < end and
            tokens[start_rest].name in {'COMMENT', UNIMPORTANT_WS}
    ):
        start_rest += 1

    rest = tokens_to_src(tokens[start_rest:end - 1])
    src = tmpl.format(args=arg_strs, rest=rest)
    tokens[start:end] = [Token('CODE', src)]


def _fix_py3_plus(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindPy3Plus()
    visitor.visit(ast_obj)

    if not any((
            visitor.bases_to_remove,
            visitor.native_literals,
            visitor.six_b,
            visitor.six_calls,
            visitor.six_raises,
            visitor.six_remove_decorators,
            visitor.six_simple,
            visitor.six_type_ctx,
            visitor.six_with_metaclass,
            visitor.super_calls,
    )):
        return contents_text

    def _replace(i, mapping, node):
        new_token = Token('CODE', _get_tmpl(mapping, node))
        if isinstance(node, ast.Name):
            tokens[i] = new_token
        else:
            j = i
            while tokens[j].src != node.attr:
                j += 1
            tokens[i:j + 1] = [new_token]

    tokens = src_to_tokens(contents_text)
    for i, token in reversed_enumerate(tokens):
        if not token.src:
            continue
        elif token.offset in visitor.bases_to_remove:
            _remove_base_class(tokens, i)
        elif token.offset in visitor.six_type_ctx:
            _replace(i, SIX_TYPE_CTX_ATTRS, visitor.six_type_ctx[token.offset])
        elif token.offset in visitor.six_simple:
            _replace(i, SIX_SIMPLE_ATTRS, visitor.six_simple[token.offset])
        elif token.offset in visitor.six_remove_decorators:
            if tokens[i - 1].src == '@':
                end = i + 1
                while tokens[end].name != 'NEWLINE':
                    end += 1
                del tokens[i - 1:end + 1]
        elif token.offset in visitor.six_b:
            j = _find_open_paren(tokens, i)
            if (
                    tokens[j + 1].name == 'STRING' and
                    _is_ascii(tokens[j + 1].src) and
                    tokens[j + 2].src == ')'
            ):
                func_args, end = _parse_call_args(tokens, j)
                _replace_call(tokens, i, end, func_args, SIX_B_TMPL)
        elif token.offset in visitor.six_calls:
            j = _find_open_paren(tokens, i)
            func_args, end = _parse_call_args(tokens, j)
            node = visitor.six_calls[token.offset]
            template = _get_tmpl(SIX_CALLS, node.func)
            _replace_call(tokens, i, end, func_args, template)
        elif token.offset in visitor.six_raises:
            j = _find_open_paren(tokens, i)
            func_args, end = _parse_call_args(tokens, j)
            node = visitor.six_raises[token.offset]
            template = _get_tmpl(SIX_RAISES, node.func)
            _replace_call(tokens, i, end, func_args, template)
        elif token.offset in visitor.six_with_metaclass:
            j = _find_open_paren(tokens, i)
            func_args, end = _parse_call_args(tokens, j)
            if len(func_args) == 1:
                tmpl = WITH_METACLASS_NO_BASES_TMPL
            else:
                tmpl = WITH_METACLASS_BASES_TMPL
            _replace_call(tokens, i, end, func_args, tmpl)
        elif token.offset in visitor.super_calls:
            i = _find_open_paren(tokens, i)
            call = visitor.super_calls[token.offset]
            victims = _victims(tokens, i, call, gen=False)
            del tokens[victims.starts[0] + 1:victims.ends[-1]]
        elif token.offset in visitor.native_literals:
            j = _find_open_paren(tokens, i)
            func_args, end = _parse_call_args(tokens, j)
            if any(tok.name == 'NL' for tok in tokens[i:end]):
                continue
            _replace_call(tokens, i, end, func_args, '{args[0]}')

    return tokens_to_src(tokens)


def _simple_arg(arg):
    return (
        isinstance(arg, ast.Name) or
        (isinstance(arg, ast.Attribute) and _simple_arg(arg.value))
    )


def _starargs(call):
    return (  # pragma: no branch (starred check uncovered in py2)
        # py2
        getattr(call, 'starargs', None) or
        getattr(call, 'kwargs', None) or
        any(k.arg is None for k in call.keywords) or (
            # py3
            getattr(ast, 'Starred', None) and
            any(isinstance(a, ast.Starred) for a in call.args)
        )
    )


class FindSimpleFormats(ast.NodeVisitor):
    def __init__(self):
        self.found = {}

    def visit_Call(self, node):  # type: (ast.Call) -> None
        if (
                isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Str) and
                node.func.attr == 'format' and
                all(_simple_arg(arg) for arg in node.args) and
                all(_simple_arg(k.value) for k in node.keywords) and
                not _starargs(node)
        ):
            seen = set()
            for _, name, spec, _ in parse_format(node.func.value.s):
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
            else:
                self.found[_ast_to_offset(node)] = node

        self.generic_visit(node)


def _unparse(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return ''.join((_unparse(node.value), '.', node.attr))
    else:
        raise NotImplementedError(ast.dump(node))


def _to_fstring(src, call):
    params = {}
    for i, arg in enumerate(call.args):
        params[str(i)] = _unparse(arg)
    for kwd in call.keywords:
        params[kwd.arg] = _unparse(kwd.value)

    parts = []
    i = 0
    for s, name, spec, conv in parse_format('f' + src):
        if name is not None:
            k, dot, rest = name.partition('.')
            name = ''.join((params[k or str(i)], dot, rest))
            i += 1
        parts.append((s, name, spec, conv))
    return unparse_parsed_string(parts)


def _fix_fstrings(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindSimpleFormats()
    visitor.visit(ast_obj)

    if not visitor.found:
        return contents_text

    tokens = src_to_tokens(contents_text)
    for i, token in reversed_enumerate(tokens):
        node = visitor.found.get(token.offset)
        if node is None:
            continue

        if _is_bytestring(token.src):  # pragma: no cover (py2-only)
            continue

        paren = i + 3
        if tokens_to_src(tokens[i + 1:paren + 1]) != '.format(':
            continue

        # we don't actually care about arg position, so we pass `node`
        victims = _victims(tokens, paren, node, gen=False)
        end = victims.ends[-1]
        # if it spans more than one line, bail
        if tokens[end].line != token.line:
            continue

        tokens[i] = token._replace(src=_to_fstring(token.src, node))
        del tokens[i + 1:end + 1]

    return tokens_to_src(tokens)


def fix_file(filename, args):
    with open(filename, 'rb') as f:
        contents_bytes = f.read()

    try:
        contents_text_orig = contents_text = contents_bytes.decode('UTF-8')
    except UnicodeDecodeError:
        print('{} is non-utf-8 (not supported)'.format(filename))
        return 1

    contents_text = _fix_py2_compatible(contents_text)
    contents_text = _fix_format_literals(contents_text)
    contents_text = _fix_tokens(contents_text, args.py3_plus)
    if not args.keep_percent_format:
        contents_text = _fix_percent_format(contents_text)
    if args.py3_plus:
        contents_text = _fix_py3_plus(contents_text)
    if args.py36_plus:
        contents_text = _fix_fstrings(contents_text)

    if contents_text != contents_text_orig:
        print('Rewriting {}'.format(filename))
        with io.open(filename, 'w', encoding='UTF-8', newline='') as f:
            f.write(contents_text)
        return 1

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('--keep-percent-format', action='store_true')
    parser.add_argument('--py3-plus', '--py3-only', action='store_true')
    parser.add_argument('--py36-plus', action='store_true')
    args = parser.parse_args(argv)

    if args.py36_plus:
        args.py3_plus = True

    ret = 0
    for filename in args.filenames:
        ret |= fix_file(filename, args)
    return ret


if __name__ == '__main__':
    exit(main())
