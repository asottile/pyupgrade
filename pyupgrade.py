from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import ast
import collections
import copy
import io
import re
import string
import tokenize


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


UNIMPORTANT_WS = 'UNIMPORTANT_WS'
NON_CODING_TOKENS = frozenset(('COMMENT', 'NL', UNIMPORTANT_WS))
Token = collections.namedtuple(
    'Token', ('name', 'src', 'line', 'utf8_byte_offset'),
)
Token.__new__.__defaults__ = (None, None,)


def tokenize_src(src):
    tokenize_target = io.StringIO(src)
    lines = (None,) + tuple(tokenize_target)
    tokenize_target.seek(0)

    tokens = []
    last_line = 1
    last_col = 0

    for (
            tok_type, tok_text, (sline, scol), (eline, ecol), line,
    ) in tokenize.generate_tokens(tokenize_target.readline):
        if sline > last_line:
            newtok = lines[last_line][last_col:]
            for lineno in range(last_line + 1, sline):
                newtok += lines[lineno]
            if scol > 0:
                newtok += lines[sline][:scol]
            if newtok:
                tokens.append(Token(UNIMPORTANT_WS, newtok))
        elif scol > last_col:
            tokens.append(Token(UNIMPORTANT_WS, line[last_col:scol]))

        tok_name = tokenize.tok_name[tok_type]
        utf8_byte_offset = len(line[:scol].encode('UTF-8'))
        tokens.append(Token(tok_name, tok_text, sline, utf8_byte_offset))
        last_line, last_col = eline, ecol

    return tokens


def untokenize_tokens(tokens):
    return ''.join(tok.src for tok in tokens)


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
    for _, fmtkey, _, _ in parsed_fmt[:-1]:
        if inty(fmtkey) and int(fmtkey) == last_int + 1:
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
    tokens = tokenize_src(contents_text)

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
        # NL is the non-breaking newline token
        elif token.name not in NON_CODING_TOKENS:
            string_start, string_end, seen_dot = None, None, False

    for start, end in reversed(to_replace):
        src = untokenize_tokens(tokens[start:end])
        new_src = _rewrite_string_literal(src)
        tokens[start:end] = [Token('STRING', new_src)]

    return untokenize_tokens(tokens)


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


def _get_victims(tokens, start, arg):
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

    # May need to remove a trailing comma
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

    set_victims = _get_victims(tokens, start + 1, arg)

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

    tokens = tokenize_src(contents_text)
    for i, token in reversed(tuple(enumerate(tokens))):
        key = (token.line, token.utf8_byte_offset)
        if key in visitor.set_empty_literals:
            _process_set_empty_literal(tokens, i)
        elif key in visitor.sets:
            _process_set_literal(tokens, i, visitor.sets[key])
    return untokenize_tokens(tokens)


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

    dict_victims = _get_victims(tokens, start + 1, arg)
    elt_victims = _get_victims(tokens, dict_victims.arg_index, arg.elt)

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

    tokens = tokenize_src(contents_text)
    for i, token in reversed(tuple(enumerate(tokens))):
        key = (token.line, token.utf8_byte_offset)
        if key in visitor.dicts:
            _process_dict_comp(tokens, i, visitor.dicts[key])
    return untokenize_tokens(tokens)


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


def _fix_unicode_literals(contents_text, py3_only):
    if not py3_only and not _imports_unicode_literals(contents_text):
        return contents_text
    tokens = tokenize_src(contents_text)
    for i, token in enumerate(tokens):
        if token.name != 'STRING':
            continue

        match = STRING_PREFIXES_RE.match(token.src)
        prefix = match.group(1)
        rest = match.group(2)
        new_prefix = prefix.replace('u', '').replace('U', '')
        tokens[i] = Token('STRING', new_prefix + rest)
    return untokenize_tokens(tokens)


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
    contents_text = _fix_unicode_literals(contents_text, args.py3_only)

    if contents_text != contents_text_orig:
        print('Rewriting {}'.format(filename))
        with io.open(filename, 'w', encoding='UTF-8') as f:
            f.write(contents_text)
        return 1

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('--py3-only', '--py3-plus', action='store_true')
    args = parser.parse_args(argv)

    ret = 0
    for filename in args.filenames:
        ret |= fix_file(filename, args)
    return ret


if __name__ == '__main__':
    exit(main())
