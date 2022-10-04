from __future__ import annotations

import io
import re
import sys
from unittest import mock

import pytest

from pyupgrade._main import main


def test_main_trivial():
    assert main(()) == 0


def test_main_noop(tmpdir, capsys):
    with pytest.raises(SystemExit):
        main(('--help',))
    out, err = capsys.readouterr()
    version_options = sorted(set(re.findall(r'--py\d+-plus', out)))

    s = '''\
from sys import version_info
x=version_info
def f():
    global x, y
'''
    f = tmpdir.join('f.py')
    f.write(s)

    assert main((f.strpath,)) == 0
    assert f.read() == s

    for version_option in version_options:
        assert main((f.strpath, version_option)) == 0
        assert f.read() == s


def test_main_changes_a_file(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('x = set((1, 2, 3))\n')
    assert main((f.strpath,)) == 1
    out, err = capsys.readouterr()
    assert err == f'Rewriting {f.strpath}\n'
    assert f.read() == 'x = {1, 2, 3}\n'


def test_main_keeps_line_endings(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary(b'x = set((1, 2, 3))\r\n')
    assert main((f.strpath,)) == 1
    assert f.read_binary() == b'x = {1, 2, 3}\r\n'


def test_main_syntax_error(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from __future__ import print_function\nprint 1\n')
    assert main((f.strpath,)) == 0


def test_main_non_utf8_bytes(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary('# -*- coding: cp1252 -*-\nx = €\n'.encode('cp1252'))
    assert main((f.strpath,)) == 1
    out, _ = capsys.readouterr()
    assert out == f'{f.strpath} is non-utf-8 (not supported)\n'


def test_keep_percent_format(tmpdir):
    f = tmpdir.join('f.py')
    f.write('"%s" % (1,)')
    assert main((f.strpath, '--keep-percent-format')) == 0
    assert f.read() == '"%s" % (1,)'
    assert main((f.strpath,)) == 1
    assert f.read() == '"{}".format(1)'


def test_keep_mock(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from mock import patch\n')
    assert main((f.strpath, '--keep-mock')) == 0
    assert f.read() == 'from mock import patch\n'
    assert main((f.strpath,)) == 1
    assert f.read() == 'from unittest.mock import patch\n'


def test_py3_plus_argument_unicode_literals(tmpdir):
    f = tmpdir.join('f.py')
    f.write('u""')
    assert main((f.strpath,)) == 1
    assert f.read() == '""'


def test_py3_plus_super(tmpdir):
    f = tmpdir.join('f.py')
    f.write(
        'class C(Base):\n'
        '    def f(self):\n'
        '        super(C, self).f()\n',
    )
    assert main((f.strpath,)) == 1
    assert f.read() == (
        'class C(Base):\n'
        '    def f(self):\n'
        '        super().f()\n'
    )


def test_py3_plus_new_style_classes(tmpdir):
    f = tmpdir.join('f.py')
    f.write('class C(object): pass\n')
    assert main((f.strpath,)) == 1
    assert f.read() == 'class C: pass\n'


def test_py3_plus_oserror(tmpdir):
    f = tmpdir.join('f.py')
    f.write('raise EnvironmentError(1, 2)\n')
    assert main((f.strpath,)) == 1
    assert f.read() == 'raise OSError(1, 2)\n'


def test_py36_plus_fstrings(tmpdir):
    f = tmpdir.join('f.py')
    f.write('"{} {}".format(hello, world)')
    assert main((f.strpath,)) == 0
    assert f.read() == '"{} {}".format(hello, world)'
    assert main((f.strpath, '--py36-plus')) == 1
    assert f.read() == 'f"{hello} {world}"'


def test_py37_plus_removes_annotations(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from __future__ import generator_stop\nx = 1\n')
    assert main((f.strpath,)) == 0
    assert main((f.strpath, '--py36-plus')) == 0
    assert main((f.strpath, '--py37-plus')) == 1
    assert f.read() == 'x = 1\n'


def test_py38_plus_removes_no_arg_decorators(tmpdir):
    f = tmpdir.join('f.py')
    f.write(
        'import functools\n\n'
        '@functools.lru_cache()\n'
        'def expensive():\n'
        '   ...',
    )
    assert main((f.strpath,)) == 0
    assert main((f.strpath, '--py36-plus')) == 0
    assert main((f.strpath, '--py37-plus')) == 0
    assert main((f.strpath, '--py38-plus')) == 1
    assert f.read() == (
        'import functools\n\n'
        '@functools.lru_cache\n'
        'def expensive():\n'
        '   ...'
    )


def test_noop_token_error(tmpdir):
    f = tmpdir.join('f.py')
    f.write(
        # force some rewrites (ast is ok https://bugs.python.org/issue2180)
        'set(())\n'
        '"%s" % (1,)\n'
        'six.b("foo")\n'
        '"{}".format(a)\n'
        # token error
        'x = \\\n'
        '5\\\n',
    )
    assert main((f.strpath, '--py36-plus')) == 0


def test_main_exit_zero_even_if_changed(tmpdir):
    f = tmpdir.join('t.py')
    f.write('set((1, 2))\n')
    assert not main((str(f), '--exit-zero-even-if-changed'))
    assert f.read() == '{1, 2}\n'
    assert not main((str(f), '--exit-zero-even-if-changed'))


def test_main_stdin_no_changes(capsys):
    stdin = io.TextIOWrapper(io.BytesIO(b'{1, 2}\n'), 'UTF-8')
    with mock.patch.object(sys, 'stdin', stdin):
        assert main(('-',)) == 0
    out, err = capsys.readouterr()
    assert out == '{1, 2}\n'


def test_main_stdin_with_changes(capsys):
    stdin = io.TextIOWrapper(io.BytesIO(b'set((1, 2))\n'), 'UTF-8')
    with mock.patch.object(sys, 'stdin', stdin):
        assert main(('-',)) == 1
    out, err = capsys.readouterr()
    assert out == '{1, 2}\n'
