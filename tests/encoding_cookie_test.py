from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    ('s', 'py3_plus'),
    (
        pytest.param(
            '# coding: utf-8\n', False,
            id='cannot remove in py2',
        ),
        pytest.param(
            '\n\n# coding: utf-8\n', True,
            id='only on first two lines',
        ),
    ),
)
def test_noop(s, py3_plus):
    assert _fix_tokens(s, py3_plus=py3_plus) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (
            '# coding: utf-8',
            '',
        ),
        (
            '# coding: us-ascii\nx = 1\n',
            'x = 1\n',
        ),
        (
            '#!/usr/bin/env python\n'
            '# coding: utf-8\n'
            'x = 1\n',

            '#!/usr/bin/env python\n'
            'x = 1\n',
        ),
    ),
)
def test_rewrite(s, expected):
    assert _fix_tokens(s, py3_plus=True) == expected
