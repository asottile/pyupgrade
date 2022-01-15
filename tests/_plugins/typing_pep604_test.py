from __future__ import annotations

import pytest
from tokenize_rt import src_to_tokens
from tokenize_rt import tokens_to_src

from pyupgrade._plugins.typing_pep604 import _fix_union


@pytest.mark.parametrize(
    ('s', 'arg_count', 'expected'),
    (
        ('Union[a, b]', 2, 'a | b'),
        ('Union[(a, b)]', 2, 'a | b'),
        ('Union[(a,)]', 1, 'a'),
        ('Union[(((a, b)))]', 2, 'a | b'),
        pytest.param('Union[((a), b)]', 2, '(a) | b', id='wat'),
        ('Union[(((a,), b))]', 2, '(a,) | b'),
        ('Union[((a,), (a, b))]', 2, '(a,) | (a, b)'),
        ('Union[((a))]', 1, 'a'),
        ('Union[a()]', 1, 'a()'),
        ('Union[a(b, c)]', 1, 'a(b, c)'),
        ('Union[(a())]', 1, 'a()'),
        ('Union[(())]', 1, '()'),
    ),
)
def test_fix_union_edge_cases(s, arg_count, expected):
    tokens = src_to_tokens(s)
    _fix_union(0, tokens, arg_count=arg_count)
    assert tokens_to_src(tokens) == expected
