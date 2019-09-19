# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    ('s', 'min_version'),
    (
        ('', (3,)),
        ('from foo import bar', (3,)),
        ('from __future__ import unknown', (3,)),
        ('from __future__ import annotations', (3,)),
        ('from __future__ import division', (2, 7)),
    ),
)
def test_future_remove_noop(s, min_version):
    assert _fix_tokens(s, min_version=min_version) == s


@pytest.mark.parametrize(
    ('s', 'min_version', 'expected'),
    (
        ('from __future__ import generators\n', (2, 7), ''),
        ('from __future__ import generators', (2, 7), ''),
        ('from __future__ import division\n', (3,), ''),
        ('from __future__ import (generators,)', (2, 7), ''),
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
            (2, 7),
            'import os.path\n',
            id='remove top-file whitespace',
        ),
    ),
)
def test_future_remove(s, min_version, expected):
    assert _fix_tokens(s, min_version=min_version) == expected
