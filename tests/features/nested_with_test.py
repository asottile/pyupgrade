from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'with a:\n'
            '    with b:\n'
            '        pass\n',
            'with (\n'
            '    a,\n'
            '    b,\n'
            '):\n'
            '    pass\n',
            id='two-level rewrite',
        ),
        pytest.param(
            'with a as x:\n'
            '    with b as y:\n'
            '        pass\n',
            'with (\n'
            '    a as x,\n'
            '    b as y,\n'
            '):\n'
            '    pass\n',
            id='rewrite preserves as-targets',
        ),
        pytest.param(
            'def f() -> None:\n'
            '    with a:\n'
            '        with b:\n'
            '            with c:\n'
            '                pass\n',
            'def f() -> None:\n'
            '    with (\n'
            '        a,\n'
            '        b,\n'
            '        c,\n'
            '    ):\n'
            '        pass\n',
            id='three-level rewrite inside function',
        ),
        pytest.param(
            'with x:\n'
            '    with y:\n'
            '        foo()\n'
            '        # blah\n'
            '        if z:\n'
            '            pass\n',
            'with (\n'
            '    x,\n'
            '    y,\n'
            '):\n'
            '    foo()\n'
            '    # blah\n'
            '    if z:\n'
            '        pass\n',
            id='rewrite preserves dedent with nested body and comment',
        ),
    ),
)
def test_fix_nested_with(s, expected):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 9))) == s
    assert _fix_plugins(s, settings=Settings(min_version=(3, 10))) == expected


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'async def f() -> None:\n'
            '    async with a:\n'
            '        async with b:\n'
            '            pass\n',
            id='skip async-with chain',
        ),
        pytest.param(
            'with a:\n'
            '    with b:\n'
            '        pass\n'
            '    x = 1\n',
            id='skip when outer body has extra statements',
        ),
        pytest.param(
            'with a, b:\n'
            '    with c:\n'
            '        pass\n',
            id='skip when outer with already has multiple items',
        ),
        pytest.param(
            'with a:\n'
            '    with b: pass\n',
            id='skip single-line nested body',
        ),
        pytest.param(
            'with a:\n'
            '\n'
            '    with b:\n'
            '        pass\n',
            id='skip blank line between nested headers',
        ),
        pytest.param(
            'with a:\n'
            '    # keep this comment\n'
            '    with b:\n'
            '        pass\n',
            id='skip comment-only line between headers',
        ),
        pytest.param(
            'with a:  # keep this comment\n'
            '    with b:\n'
            '        pass\n',
            id='skip comment on outer header',
        ),
        pytest.param(
            'with a:\n'
            '    with b:  # keep this comment\n'
            '        pass\n',
            id='skip comment on inner header',
        ),
    ),
)
def test_fix_nested_with_noop(s):
    assert _fix_plugins(s, settings=Settings(min_version=(3, 10))) == s
