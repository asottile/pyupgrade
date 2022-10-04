from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'min_version'),
    (
        ('', (3,)),
        ('from foo import bar', (3,)),
        ('from __future__ import unknown', (3,)),
        ('from __future__ import annotations', (3,)),
        ('from six import *', (3,)),
        ('from six.moves import map as notmap', (3,)),
        ('from unrelated import queue as map', (3,)),
        pytest.param(
            'if True:\n'
            '    from six.moves import map\n',
            (3,),
            id='import removal not at module scope',
        ),
    ),
)
def test_import_removals_noop(s, min_version):
    assert _fix_plugins(s, settings=Settings(min_version=min_version)) == s


@pytest.mark.parametrize(
    ('s', 'min_version', 'expected'),
    (
        ('from __future__ import generators\n', (3,), ''),
        ('from __future__ import generators', (3,), ''),
        ('from __future__ import division\n', (3,), ''),
        ('from __future__ import division\n', (3, 6), ''),
        ('from __future__ import (generators,)', (3,), ''),
        ('from __future__ import print_function', (3, 8), ''),
        ('from builtins import map', (3,), ''),
        ('from builtins import *', (3,), ''),
        ('from six.moves import map', (3,), ''),
        ('from six.moves.builtins import map', (3,), ''),
        pytest.param(
            'from __future__ import absolute_import, annotations\n',
            (3,),
            'from __future__ import annotations\n',
            id='remove at beginning single line',
        ),
        pytest.param(
            'from __future__ import (\n'
            '    absolute_import,\n'
            '    annotations,\n'
            ')',
            (3,),
            'from __future__ import (\n'
            '    annotations,\n'
            ')',
            id='remove at beginning paren continuation',
        ),
        pytest.param(
            'from __future__ import \\\n'
            '    absolute_import, \\\n'
            '    annotations\n',
            (3,),
            'from __future__ import \\\n'
            '    annotations\n',
            id='remove at beginning backslash continuation',
        ),
        pytest.param(
            'from __future__ import annotations, absolute_import\n',
            (3,),
            'from __future__ import annotations\n',
            id='remove at end single line',
        ),
        pytest.param(
            'from __future__ import (\n'
            '    annotations,\n'
            '    absolute_import,\n'
            ')',
            (3,),
            'from __future__ import (\n'
            '    annotations,\n'
            ')',
            id='remove at end paren continuation',
        ),
        pytest.param(
            'from __future__ import \\\n'
            '    annotations, \\\n'
            '    absolute_import\n',
            (3,),
            'from __future__ import \\\n'
            '    annotations\n',
            id='remove at end backslash continuation',
        ),
        pytest.param(
            'from __future__ import (\n'
            '    absolute_import,\n'
            '    annotations,\n'
            '    division,\n'
            ')',
            (3,),
            'from __future__ import (\n'
            '    annotations,\n'
            ')',
            id='remove multiple',
        ),
        pytest.param(
            'from __future__ import with_statement\n'
            '\n'
            'import os.path\n',
            (3,),
            'import os.path\n',
            id='remove top-file whitespace',
        ),
        pytest.param(
            'from six . moves import map', (3,), '',
            id='weird whitespace in dotted name',
        ),
        pytest.param(
            'from io import open, BytesIO as BIO\n'
            'from io import BytesIO as BIO, open\n',
            (3,),
            'from io import BytesIO as BIO\n'
            'from io import BytesIO as BIO\n',
            id='removal with import-as',
        ),
    ),
)
def test_import_removals(s, min_version, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=min_version))
    assert ret == expected
