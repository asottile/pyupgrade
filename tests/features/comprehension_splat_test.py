from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    's',
    (
        '[x for a in b for x in a]',
        '{x for a in b for x in a}',
        '(x for a in b for x in a)',
        '{k: v for a in b for k, v in a.items()}',
        pytest.param(
            'foo(x for x in y)',
            id='this would chang behaviour: genexpr to args',
        ),
    ),
)
def test_noop_before_315(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 14))) == s


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '[x async for a in b async for x in a]',
            id='not allowed for async final comprehension list',
        ),
        pytest.param(
            '[x for a in b for x in a if x % 2 == 0]',
            id='not allowed when conditions occur list',
        ),
        pytest.param(
            '{k: v for a in b async for k, v in a.items()}',
            id='not allowed for async final comprehension dict',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a.items() if x % 2 == 0}',
            id='not allowed when conditions occur dict',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a.items(1)}',
            id='unrelated items call args',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a.items(n=1)}',
            id='unrelated items call kwargs',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a}',
            id='no items call',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a.iteritems()}',
            id='not an items call',
        ),
    ),
)
def test_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 15))) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            '[x for a in b for x in a]',
            '[*a for a in b]',
            id='listcomp',
        ),
        pytest.param(
            '{x for a in b for x in a}',
            '{*a for a in b}',
            id='setcomp',
        ),
        pytest.param(
            '(x for a in b for x in a)',
            '(*a for a in b)',
            id='genexp',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a.items()}',
            '{**a for a in b}',
            id='dictcomp',
        ),
        pytest.param(
            '[x async for a in b for x in a]',
            '[*a async for a in b]',
            id='async',
        ),
        pytest.param(
            '[x for a in b for x in a.whatever()]',
            '[*a.whatever() for a in b]',
            id='alternative loop variable list',
        ),
        pytest.param(
            '{k: v for a in b for k, v in a.whatever().items()}',
            '{**a.whatever() for a in b}',
            id='alternative loop variable dict',
        ),
        pytest.param(
            'print(x for a in b for x in a)',
            'print(*a for a in b)',
            id='generator in a call',
        ),
        pytest.param(
            '[(x)for(a)in(b)for(x)in(a)]',
            '[*(a)for(a)in(b)]',
            id='evil list parens',
        ),
        pytest.param(
            '{(k):(v)for(a)in(b)for(k),(v)in(((a).items)())}',
            '{**(a)for(a)in(b)}',
            id='evil dict parens',
        ),
        pytest.param(
            '{(k):(v)for(a)in(b)for(k),(v)in( ((a).items)())}',
            '{**(a)for(a)in(b)}',
            id='evil dict parens 2',
        ),
    ),
)
def test_fix(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 15)))
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            '[x for x in y]',
            '[*y]',
            id='trivial list replace',
        ),
        pytest.param(
            '{k: v for k, v in dct.items()}',
            '{**dct}',
            id='trivial dict replace',
        ),
    ),
)
def test_fix_always(s, expected):
    ret = _fix_plugins(s, settings=Settings())
    assert ret == expected
