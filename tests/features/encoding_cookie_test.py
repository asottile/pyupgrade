from __future__ import annotations

import pytest

from pyupgrade._main import _fix_tokens


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '# line 1\n# line 2\n# coding: utf-8\n',
            id='only on first two lines',
        ),
    ),
)
def test_noop(s):
    assert _fix_tokens(s) == s


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
    assert _fix_tokens(s) == expected
