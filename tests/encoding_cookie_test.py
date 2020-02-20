import pytest

from pyupgrade import _fix_tokens


@pytest.mark.parametrize(
    ('s', 'min_version'),
    (
        pytest.param(
            '# coding: utf-8\n', (2, 7),
            id='cannot remove in py2',
        ),
        pytest.param(
            '# line 1\n# line 2\n# coding: utf-8\n', (3,),
            id='only on first two lines',
        ),
    ),
)
def test_noop(s, min_version):
    assert _fix_tokens(s, min_version=min_version) == s


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
    assert _fix_tokens(s, min_version=(3,)) == expected
