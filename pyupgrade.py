from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import ast
import collections
import io
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


def _is_wtf_set(tokens, i):
    return tokens[i].src != 'set' or tokens[i + 1].src != '('


def _process_set_empty_literal(tokens, start):
    if _is_wtf_set(tokens, start):
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


def _process_set_literal(tokens, start, arg):
    if _is_wtf_set(tokens, start):
        return

    def _is_arg(token):
        return (
            token.line == arg.lineno and
            token.utf8_byte_offset == arg.col_offset
        )

    i = start + 2
    brace_stack = ['(']
    seen_arg = False
    victim_start_braces = []
    victim_start_depths = []
    victim_end_braces = []

    while brace_stack:
        token = tokens[i].src
        is_start_brace = token in BRACES
        is_end_brace = token == BRACES[brace_stack[-1]]

        if is_start_brace:
            brace_stack.append(token)

        # If we haven't seen our token yet, there are potentially victim
        # unnecessary parens to remove
        if is_start_brace and not seen_arg:
            victim_start_braces.append(i)
            victim_start_depths.append(len(brace_stack))
        if _is_arg(tokens[i]):
            seen_arg = True
        if is_end_brace and len(brace_stack) in victim_start_depths:
            victim_end_braces.append(i)

        if is_end_brace:
            brace_stack.pop()

        i += 1

    tokens[i - 1] = Token('OP', '}')
    for index in reversed(victim_start_braces + victim_end_braces):
        del tokens[index]
    tokens[start:start + 2] = [Token('OP', '{')]


def _fix_sets(contents_text, filename):
    contents_bytes = contents_text.encode('UTF-8')
    ast_obj = ast.parse(contents_bytes, filename=filename)
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


def fix_file(filename):  # pragma: no cover (EVENTUALLY!)
    with io.open(filename, encoding='UTF-8') as f:
        contents_text_orig = contents_text = f.read()

    contents_text = _fix_sets(contents_text, filename)

    if contents_text != contents_text_orig:
        with io.open(filename, 'w', encoding='UTF-8') as f:
            f.write(contents_text)
        return 1

    return 0


def main(argv=None):  # pragma: no cover (EVENTUALLY!)
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    ret = 0
    for filename in args.filenames:
        ret |= fix_file(filename)
    return ret


if __name__ == '__main__':
    exit(main())
