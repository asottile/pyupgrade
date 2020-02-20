import pytest

from pyupgrade import _fix_py3_plus


@pytest.mark.parametrize(
    's',
    (
        # syntax error
        'x = (',
        # unrelated
        'from os import path',
        'from six import moves',
        # unrelated decorator
        '@mydec\n'
        'class C: pass',
        # renaming things for weird reasons
        'from six import StringIO as text_type\n'
        'isinstance(s, text_type)\n',
        # don't rewrite things that would become `raise` in non-statements
        'print(six.raise_from(exc, exc_from))',
        # non-ascii bytestring
        'print(six.b("£"))',
        # extra whitespace
        'print(six.b(   "123"))',
        # intentionally not handling this case due to it being a bug (?)
        'class C(six.with_metaclass(Meta, B), D): pass',
        # cannot determine args to rewrite them
        'six.reraise(*err)', 'six.b(*a)', 'six.u(*a)',
        'class C(six.with_metaclass(*a)): pass',
        '@six.add_metaclass(*a)\n'
        'class C: pass\n',
        # parenthesized part of attribute
        '(\n'
        '    six\n'
        ').text_type(u)\n',
        # next is shadowed
        'next()',
    ),
)
def test_fix_six_noop(s):
    assert _fix_py3_plus(s) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'isinstance(s, six.text_type)',
            'isinstance(s, str)',
        ),
        pytest.param(
            'isinstance(s, six   .    string_types)',
            'isinstance(s, str)',
            id='weird spacing on six.attr',
        ),
        (
            'isinstance(s, six.string_types)',
            'isinstance(s, str)',
        ),
        (
            'issubclass(tp, six.string_types)',
            'issubclass(tp, str)',
        ),
        (
            'STRING_TYPES = six.string_types',
            'STRING_TYPES = (str,)',
        ),
        (
            'from six import string_types\n'
            'isinstance(s, string_types)\n',

            'from six import string_types\n'
            'isinstance(s, str)\n',
        ),
        (
            'from six import string_types\n'
            'STRING_TYPES = string_types\n',

            'from six import string_types\n'
            'STRING_TYPES = (str,)\n',
        ),
        (
            'six.b("123")',
            'b"123"',
        ),
        (
            'six.b(r"123")',
            'br"123"',
        ),
        (
            r'six.b("\x12\xef")',
            r'b"\x12\xef"',
        ),
        (
            'six.ensure_binary("foo")',
            'b"foo"',
        ),
        (
            'from six import b\n\n' r'b("\x12\xef")',
            'from six import b\n\n' r'b"\x12\xef"',
        ),
        (
            'six.byte2int(b"f")',
            'b"f"[0]',
        ),
        (
            '@six.python_2_unicode_compatible\n'
            'class C: pass',

            'class C: pass',
        ),
        (
            '@six.python_2_unicode_compatible\n'
            '@other_decorator\n'
            'class C: pass',

            '@other_decorator\n'
            'class C: pass',
        ),
        pytest.param(
            '@  six.python_2_unicode_compatible\n'
            'class C: pass\n',

            'class C: pass\n',

            id='weird spacing at the beginning python_2_unicode_compatible',
        ),
        (
            'from six import python_2_unicode_compatible\n'
            '@python_2_unicode_compatible\n'
            'class C: pass',

            'from six import python_2_unicode_compatible\n'
            'class C: pass',
        ),
        (
            'six.get_unbound_function(meth)\n',
            'meth\n',
        ),
        (
            'from six import get_unbound_function\n'
            'get_unbound_function(meth)\n',

            'from six import get_unbound_function\n'
            'meth\n',
        ),
        (
            'six.indexbytes(bs, i)\n',
            'bs[i]\n',
        ),
        (
            'six.assertCountEqual(\n'
            '   self,\n'
            '   arg1,\n'
            '   arg2,\n'
            ')',

            'self.assertCountEqual(\n'
            '   arg1,\n'
            '   arg2,\n'
            ')',
        ),
        (
            'six.assertCountEqual(\n'
            '   self,\\\n'
            '   arg1,\n'
            '   arg2,\n'
            ')',

            'self.assertCountEqual(\\\n'
            '   arg1,\n'
            '   arg2,\n'
            ')',
        ),
        (
            'six.assertCountEqual(\n'
            '   self,  # hello\n'
            '   arg1,\n'
            '   arg2,\n'
            ')',

            'self.assertCountEqual(\n'
            '   arg1,\n'
            '   arg2,\n'
            ')',
        ),
        (
            'six.assertCountEqual(\n'
            '   self,\n'
            '   arg1,\n'
            '   (1, 2, 3),\n'
            ')',

            'self.assertCountEqual(\n'
            '   arg1,\n'
            '   (1, 2, 3),\n'
            ')',
        ),
        pytest.param(
            'six.u ("bar")',
            '"bar"',
            id='weird spacing six.u',
        ),
        pytest.param(
            'from six import u\nu ("bar")',
            'from six import u\n"bar"',
            id='weird spacing u',
        ),
        (
            'six.raise_from(exc, exc_from)\n',
            'raise exc from exc_from\n',
        ),
        (
            'six.reraise(tp, exc, tb)\n',
            'raise exc.with_traceback(tb)\n',
        ),
        (
            'six.reraise(tp, exc)\n',
            'raise exc.with_traceback(None)\n',
        ),
        (
            'from six import raise_from\n'
            'raise_from(exc, exc_from)\n',

            'from six import raise_from\n'
            'raise exc from exc_from\n',
        ),
        (
            'six.reraise(\n'
            '   tp,\n'
            '   exc,\n'
            '   tb,\n'
            ')\n',
            'raise exc.with_traceback(tb)\n',
        ),
        pytest.param(
            'six.raise_from (exc, exc_from)',
            'raise exc from exc_from',
            id='weird spacing six.raise_from',
        ),
        pytest.param(
            'from six import raise_from\nraise_from (exc, exc_from)',
            'from six import raise_from\nraise exc from exc_from',
            id='weird spacing raise_from',
        ),
        (
            'class C(six.with_metaclass(M)): pass',

            'class C(metaclass=M): pass',
        ),
        (
            'class C(six.with_metaclass(M, B)): pass',

            'class C(B, metaclass=M): pass',
        ),
        (
            'class C(six.with_metaclass(M, B1, B2)): pass',

            'class C(B1, B2, metaclass=M): pass',
        ),
        (
            'from six import with_metaclass\n'
            'class C(with_metaclass(M, B)): pass\n',

            'from six import with_metaclass\n'
            'class C(B, metaclass=M): pass\n',
        ),
        pytest.param(
            'class C(six.with_metaclass (M, B)): pass',
            'class C(B, metaclass=M): pass',
            id='weird spacing six.with_metaclass',
        ),
        pytest.param(
            'from six import with_metaclass\n'
            'class C(with_metaclass (M, B)): pass',

            'from six import with_metaclass\n'
            'class C(B, metaclass=M): pass',

            id='weird spacing with_metaclass',
        ),
        pytest.param(
            'from six import with_metaclass\n'
            'class C(with_metaclass(M, object)): pass',

            'from six import with_metaclass\n'
            'class C(metaclass=M): pass',

            id='elide object base in with_metaclass',
        ),
        pytest.param(
            '@six.add_metaclass(M)\n'
            'class C: pass\n',

            'class C(metaclass=M): pass\n',

            id='basic six.add_metaclass',
        ),
        pytest.param(
            'from six import add_metaclass\n'
            '@add_metaclass(M)\n'
            'class C: pass\n',

            'from six import add_metaclass\n'
            'class C(metaclass=M): pass\n',

            id='basic add_metaclass',
        ),
        pytest.param(
            '@six.add_metaclass(M)\n'
            'class C(): pass\n',

            'class C(metaclass=M): pass\n',

            id='basic six.add_metaclass, no bases but parens',
        ),
        pytest.param(
            '@six.add_metaclass(M)\n'
            'class C(A): pass\n',

            'class C(A, metaclass=M): pass\n',

            id='add_metaclass, one base',
        ),
        pytest.param(
            '@six.add_metaclass(M)\n'
            'class C(\n'
            '    A,\n'
            '): pass\n',

            'class C(\n'
            '    A, metaclass=M,\n'
            '): pass\n',

            id='add_metaclass, base with trailing comma',
        ),
        pytest.param(
            'x = (object,)\n'
            '@six.add_metaclass(M)\n'
            'class C(x[:][0]): pass\n',

            'x = (object,)\n'
            'class C(x[:][0], metaclass=M): pass\n',

            id='add_metaclass, weird base that contains a :',
        ),
        pytest.param(
            'if True:\n'
            '    @six.add_metaclass(M)\n'
            '    class C: pass\n',

            'if True:\n'
            '    class C(metaclass=M): pass\n',

            id='add_metaclass, indented',
        ),
        pytest.param(
            'print(six.itervalues({1:2}))\n',
            'print({1:2}.values())\n',
            id='six.itervalues',
        ),
        pytest.param(
            'print(next(six.itervalues({1:2})))\n',
            'print(next(iter({1:2}.values())))\n',
            id='six.itervalues inside next(...)',
        ),
    ),
)
def test_fix_six(s, expected):
    assert _fix_py3_plus(s) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            'import six\n\nclass C(six.Iterator): pass',
            'import six\n\nclass C: pass',
        ),
        (
            'from six import Iterator\n'
            '\n'
            'class C(Iterator): pass',
            'from six import Iterator\n'
            '\n'
            'class C: pass',
        ),
        (
            'import six\n'
            '\n'
            'class C(\n'
            '    six.Iterator,\n'
            '): pass',
            'import six\n'
            '\n'
            'class C: pass',
        ),
        (
            'class C(object, six.Iterator): pass',
            'class C: pass',
        ),
        (
            'class C(six.Iterator, metaclass=ABCMeta): pass',
            'class C(metaclass=ABCMeta): pass',
        ),
        (
            'class C(six.Iterator, object, metaclass=ABCMeta): pass',
            'class C(metaclass=ABCMeta): pass',
        ),
        (
            'from six import Iterator\n'
            '\n'
            'class C(Iterator, metaclass=ABCMeta): pass',
            'from six import Iterator\n'
            '\n'
            'class C(metaclass=ABCMeta): pass',
        ),
    ),
)
def test_fix_base_classes(s, expected):
    assert _fix_py3_plus(s) == expected
