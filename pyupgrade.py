from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import ast
import collections
import copy
import io
import re
import string

from tokenize_rt import ESCAPED_NL
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


def ast_parse(contents_text):
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
        # Wellp, the format literal was malformed, so skip it
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
SET_TRANSFORM = (ast.List, ast.ListComp, ast.GeneratorExp, ast.Tuple)
Offset = collections.namedtuple('Offset', ('line', 'utf8_byte_offset'))


class FindSetsVisitor(ast.NodeVisitor):
    def __init__(self):
        self.sets = {}
        self.set_empty_literals = {}

    def visit_Call(self, node):
        if (
                isinstance(node.func, ast.Name) and
                node.func.id == 'set' and
                len(node.args) == 1 and
                not _has_kwargs(node) and
                isinstance(node.args[0], SET_TRANSFORM)
        ):
            arg, = node.args
            key = Offset(node.func.lineno, node.func.col_offset)
            if (
                    isinstance(arg, (ast.List, ast.Tuple)) and
                    len(arg.elts) == 0
            ):
                self.set_empty_literals[key] = arg
            else:
                self.sets[key] = arg

        self.generic_visit(node)


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


def _is_arg(token, arg):
    return (
        token.line == arg.lineno and token.utf8_byte_offset == arg.col_offset
    )


def _adjust_arg(tokens, i, arg):
    # Adjust `arg` to be the position of the first element.
    # listcomps, generators, and tuples already point to the first element
    if isinstance(arg, ast.List) and not isinstance(arg.elts[0], ast.Tuple):
        arg = arg.elts[0]
    elif isinstance(arg, ast.List):
        # If the first element is a tuple, the ast lies to us about its col
        # offset.  We must find the first `(` token after the start of the
        # list element.
        while not _is_arg(tokens[i], arg):
            i += 1
        while tokens[i].src != '(':
            i += 1
        arg = copy.copy(arg.elts[0])
        arg.lineno = tokens[i].line
        arg.col_offset = tokens[i].utf8_byte_offset
    return arg


Victims = collections.namedtuple(
    'Victims', ('starts', 'ends', 'first_comma_index', 'arg_index'),
)


def _victims(tokens, start, arg, gen):
    arg = _adjust_arg(tokens, start, arg)

    starts = [start]
    start_depths = [1]
    ends = []
    first_comma_index = None
    arg_depth = None
    arg_index = None
    brace_stack = [tokens[start].src]
    i = start + 1

    while brace_stack:
        token = tokens[i].src
        is_start_brace = token in BRACES
        is_end_brace = token == BRACES[brace_stack[-1]]

        if _is_arg(tokens[i], arg):
            arg_depth = len(brace_stack)
            arg_index = i

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


def _fix_sets(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text
    visitor = FindSetsVisitor()
    visitor.visit(ast_obj)
    if not visitor.sets and not visitor.set_empty_literals:
        return contents_text

    tokens = src_to_tokens(contents_text)
    for i, token in reversed(tuple(enumerate(tokens))):
        key = (token.line, token.utf8_byte_offset)
        if key in visitor.set_empty_literals:
            _process_set_empty_literal(tokens, i)
        elif key in visitor.sets:
            _process_set_literal(tokens, i, visitor.sets[key])
    return tokens_to_src(tokens)


class FindDictsVisitor(ast.NodeVisitor):
    def __init__(self):
        self.dicts = {}

    def visit_Call(self, node):
        if (
                isinstance(node.func, ast.Name) and
                node.func.id == 'dict' and
                len(node.args) == 1 and
                not _has_kwargs(node) and
                isinstance(node.args[0], (ast.ListComp, ast.GeneratorExp)) and
                isinstance(node.args[0].elt, (ast.Tuple, ast.List)) and
                len(node.args[0].elt.elts) == 2
        ):
            arg, = node.args
            key = Offset(node.func.lineno, node.func.col_offset)
            self.dicts[key] = arg
        self.generic_visit(node)


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


def _fix_dictcomps(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text
    visitor = FindDictsVisitor()
    visitor.visit(ast_obj)
    if not visitor.dicts:
        return contents_text

    tokens = src_to_tokens(contents_text)
    for i, token in reversed(tuple(enumerate(tokens))):
        key = (token.line, token.utf8_byte_offset)
        if key in visitor.dicts:
            _process_dict_comp(tokens, i, visitor.dicts[key])
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


def _fix_unicode_literals(contents_text, py3_plus):
    if not py3_plus and not _imports_unicode_literals(contents_text):
        return contents_text
    tokens = src_to_tokens(contents_text)
    for i, token in enumerate(tokens):
        if token.name != 'STRING':
            continue

        match = STRING_PREFIXES_RE.match(token.src)
        prefix = match.group(1)
        rest = match.group(2)
        new_prefix = prefix.replace('u', '').replace('U', '')
        tokens[i] = Token('STRING', new_prefix + rest)
    return tokens_to_src(tokens)


def _fix_long_literals(contents_text):
    tokens = src_to_tokens(contents_text)
    for i, token in enumerate(tokens):
        if token.name == 'NUMBER':
            tokens[i] = token._replace(src=token.src.rstrip('lL'))
    return tokens_to_src(tokens)


def _fix_octal_literals(contents_text):
    def _fix_octal(s):
        if not s.startswith('0') or not s.isdigit() or s == len(s) * '0':
            return s
        else:  # pragma: no cover (py2 only)
            return '0o' + s[1:]

    tokens = src_to_tokens(contents_text)
    for i, token in enumerate(tokens):
        if token.name == 'NUMBER':
            tokens[i] = token._replace(src=_fix_octal(token.src))
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

    def visit_BinOp(self, node):
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
                self.found[Offset(node.lineno, node.col_offset)] = node
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
        seen_keys.add(k.s)
        keys[Offset(k.lineno, k.col_offset)] = k

    # TODO: this is overly timid
    brace = start + 4
    if tokens_to_src(tokens[start + 1:brace + 1]) != ' % {':
        return

    victims = _victims(tokens, brace, node.right, gen=False)
    brace_end = victims.ends.pop()

    key_indices = []
    for i, token in enumerate(tokens[brace:brace_end], brace):
        k = keys.pop(Offset(token.line, token.utf8_byte_offset), None)
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
    for index in reversed(victims.starts + victims.ends):
        _remove_brace(tokens, index)
    newsrc = _percent_to_format(tokens[start].src)
    tokens[start] = tokens[start]._replace(src=newsrc)
    tokens[start + 1:brace] = [Token('Format', '.format'), Token('OP', '(')]


def _fix_percent_format(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindPercentFormats()
    visitor.visit(ast_obj)

    tokens = src_to_tokens(contents_text)

    for i, token in reversed(tuple(enumerate(tokens))):
        node = visitor.found.get(Offset(token.line, token.utf8_byte_offset))
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

    def visit_Call(self, node):
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
                    seen.add(candidate)
            else:
                self.found[Offset(node.lineno, node.col_offset)] = node

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
    for i, (s, name, spec, conv) in enumerate(parse_format('f' + src)):
        if name is not None:
            k, dot, rest = name.partition('.')
            name = ''.join((params[k or str(i)], dot, rest))
        parts.append((s, name, spec, conv))
    return unparse_parsed_string(parts)


def _fix_fstrings(contents_text):
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    visitor = FindSimpleFormats()
    visitor.visit(ast_obj)

    tokens = src_to_tokens(contents_text)
    for i, token in reversed(tuple(enumerate(tokens))):
        node = visitor.found.get(Offset(token.line, token.utf8_byte_offset))
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

    contents_text = _fix_dictcomps(contents_text)
    contents_text = _fix_sets(contents_text)
    contents_text = _fix_format_literals(contents_text)
    contents_text = _fix_unicode_literals(contents_text, args.py3_plus)
    contents_text = _fix_long_literals(contents_text)
    contents_text = _fix_octal_literals(contents_text)
    contents_text = _fix_percent_format(contents_text)
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
