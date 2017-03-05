from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import ast
import string


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


SET_REMOVE = {
    ast.Tuple: ('(', ')'), ast.List: ('[', ']'), ast.ListComp: ('[', ']'),
}
SET_TRANSFORM = tuple(SET_REMOVE) + (ast.GeneratorExp,)


class Visitor(ast.NodeVisitor):  # pragma: no cover (EVENTUALLY!)
    def visit_Attribute(self, node):
        if node.attr == 'format' and isinstance(node.value, ast.Str):
            s = node.value.s
            try:
                rt = unparse_parsed_string(parse_format(s))
            except Exception as e:
                print('{!r}: {!r}'.format(e, s))
            else:
                if not (type(rt), rt) == (type(s), s):
                    print('{!r} {!r}'.format(s, rt))

        self.generic_visit(node)

    def visit_Call(self, node):
        if (
                isinstance(node.func, ast.Name) and
                node.func.id == 'set' and
                len(node.args) == 1 and
                isinstance(node.args[0], SET_TRANSFORM)
        ):
            # py2+py3: these are (logical line, *byte* offset)
            # py2 (tokenze, bytes) => (logical line, *byte* offset)
            # py2 (tokenize, text) => (logical line, char offset)
            # py3 (tokenize requires bytes) => (logical line, char offset)
            print('{}:{}: set'.format(node.func.lineno, node.func.col_offset))

        self.generic_visit(node)


def fix_file(filename):  # pragma: no cover (EVENTUALLY!)
    with open(filename, 'rb') as f:
        contents = f.read()

    ast_obj = ast.parse(contents, filename=filename)
    Visitor().visit(ast_obj)
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
