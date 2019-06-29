# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pyupgrade import _fix_py3_plus
from pyupgrade import FindPy3Plus


@pytest.mark.parametrize('alias', FindPy3Plus.OS_ERROR_ALIASES)
@pytest.mark.parametrize(
    ('tpl', 'expected'),
    (
        ('x = {alias}', 'x = OSError'),
        ('x = {alias}()', 'x = OSError()'),
        ('x = {alias}(1, 2)', 'x = OSError(1, 2)'),
        (
            'x = {alias}(\n'
            '    1,\n'
            '    2,\n'
            ')',
            'x = OSError(\n'
            '    1,\n'
            '    2,\n'
            ')',
        ),
        ('raise {alias}', 'raise OSError'),
        ('raise {alias}()', 'raise OSError()'),
        ('raise {alias}(1, 2)', 'raise OSError(1, 2)'),
        (
            'raise {alias}(\n'
            '    1,\n'
            '    2,\n'
            ')',
            'raise OSError(\n'
            '    1,\n'
            '    2,\n'
            ')',
        ),
    ),
)
def test_fix_oserror_aliases(alias, tpl, expected):
    s = tpl.format(alias=alias)
    assert _fix_py3_plus(s) == expected
