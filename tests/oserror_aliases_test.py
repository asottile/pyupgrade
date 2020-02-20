import pytest

from pyupgrade import _fix_py3_plus
from pyupgrade import FindPy3Plus


@pytest.mark.parametrize('alias', FindPy3Plus.OS_ERROR_ALIASES)
@pytest.mark.parametrize(
    ('tpl', 'expected'),
    (
        (
            'try:\n'
            '    pass\n'
            'except {alias}:\n'
            '    pass\n',

            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'try:\n'
            '    pass\n'
            'except ({alias},):\n'
            '    pass\n',

            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'try:\n'
            '    pass\n'
            'except ({alias}, KeyError, OSError):\n'
            '    pass\n',

            'try:\n'
            '    pass\n'
            'except (OSError, KeyError):\n'
            '    pass\n',
        ),
        (
            'try:\n'
            '    pass\n'
            'except ({alias}, OSError, IOError):\n'
            '    pass\n',

            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'try:\n'
            '    pass\n'
            'except({alias}, OSError, IOError):\n'
            '    pass\n',

            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
    ),
)
def test_fix_oserror_aliases_try(alias, tpl, expected):
    s = tpl.format(alias=alias)
    assert _fix_py3_plus(s) == expected


@pytest.mark.parametrize(
    's',
    (
        # empty try-except
        'try:\n'
        '    pass\n'
        'except:\n'
        '    pass\n',
        # no exception to rewrite
        'try:\n'
        '    pass\n'
        'except AssertionError:\n'
        '    pass\n',
        # no exception to rewrite
        'try:\n'
        '    pass\n'
        'except ('
        '   AssertionError,'
        '):\n'
        '    pass\n',
        # already correct
        'try:\n'
        '    pass\n'
        'except OSError:\n'
        '    pass\n',
        # already correct
        'try:\n'
        '    pass\n'
        'except (OSError, KeyError):\n'
        '    pass\n',
    ),
)
def test_fix_oserror_aliases_noop(s):
    assert _fix_py3_plus(s) == s


@pytest.mark.parametrize('imp', FindPy3Plus.OS_ERROR_ALIAS_MODULES)
@pytest.mark.parametrize(
    'tpl',
    (
        # if the error isn't in a try or except it shouldn't be rewritten
        # to avoid false positives
        'from {imp} import error\n\n'
        'def foo():\n'
        '     error = 3\n',
        '     return error\n',
        # renaming things for weird reasons
        'from {imp} import error as the_roof\n'
        'raise the_roof()\n',
    ),
)
def test_fix_oserror_aliases_noop_tpl(imp, tpl):
    s = tpl.format(imp=imp)
    assert _fix_py3_plus(s) == s


@pytest.mark.parametrize('imp', FindPy3Plus.OS_ERROR_ALIAS_MODULES)
@pytest.mark.parametrize(
    ('tpl', 'expected_tpl'),
    (
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except {imp}.error:\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except ({imp}.error,):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except ({imp}.error, KeyError, OSError):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except (OSError, KeyError):\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except ({imp}.error, OSError, IOError):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except (OSError, {imp}.error, IOError):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except (OSError, {imp}.error, IOError):\n'
            '    pass\n'
            'except (OSError, {imp}.error, KeyError):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n'
            'except (OSError, KeyError):\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except({imp}.error, OSError, IOError):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except('
            '   {imp}.error,'
            '   OSError,'
            '   IOError,'
            '):\n'
            '    pass\n',

            'import {imp}\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except error:\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except (error,):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except (error, KeyError, OSError):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except (OSError, KeyError):\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except (error, OSError, IOError):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except (OSError, error, OSError):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except (OSError, error, OSError):\n'
            '    pass\n'
            'except (OSError, error, KeyError):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n'
            'except (OSError, KeyError):\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except(error, OSError, IOError):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
        (
            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except('
            '   error,'
            '   OSError,'
            '   IOError,'
            '):\n'
            '    pass\n',

            'from {imp} import error\n\n'
            'try:\n'
            '    pass\n'
            'except OSError:\n'
            '    pass\n',
        ),
    ),
)
def test_fix_oserror_complex_aliases_try(imp, tpl, expected_tpl):
    s, expected = tpl.format(imp=imp), expected_tpl.format(imp=imp)
    assert _fix_py3_plus(s) == expected


@pytest.mark.parametrize('alias', FindPy3Plus.OS_ERROR_ALIASES)
@pytest.mark.parametrize(
    ('tpl', 'expected'),
    (
        ('raise {alias}', 'raise OSError'),
        ('raise {alias}()', 'raise OSError()'),
        ('raise {alias}(1)', 'raise OSError(1)'),
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
def test_fix_oserror_aliases_raise(alias, tpl, expected):
    s = tpl.format(alias=alias)
    assert _fix_py3_plus(s) == expected


@pytest.mark.parametrize('imp', FindPy3Plus.OS_ERROR_ALIAS_MODULES)
@pytest.mark.parametrize(
    ('tpl', 'expected_tpl'),
    (
        (
            'import {imp}\n\n'
            'raise {imp}.error\n',

            'import {imp}\n\n'
            'raise OSError\n',
        ),
        (
            'import {imp}\n\n'
            'raise {imp}.error()\n',

            'import {imp}\n\n'
            'raise OSError()\n',
        ),
        (
            'import {imp}\n\n'
            'raise {imp}.error(1)\n',

            'import {imp}\n\n'
            'raise OSError(1)\n',
        ),
        (
            'import {imp}\n\n'
            'raise {imp}.error(1, 2)\n',

            'import {imp}\n\n'
            'raise OSError(1, 2)\n',
        ),
        (
            'import {imp}\n\n'
            'raise {imp}.error(\n'
            '    1,\n'
            '    2,\n'
            ')',

            'import {imp}\n\n'
            'raise OSError(\n'
            '    1,\n'
            '    2,\n'
            ')',
        ),
        (
            'from {imp} import error\n\n'
            'raise error\n',

            'from {imp} import error\n\n'
            'raise OSError\n',
        ),
        (
            'from {imp} import error\n\n'
            'raise error()\n',

            'from {imp} import error\n\n'
            'raise OSError()\n',
        ),
        (
            'from {imp} import error\n\n'
            'raise error(1)\n',

            'from {imp} import error\n\n'
            'raise OSError(1)\n',
        ),
        (
            'from {imp} import error\n\n'
            'raise error(1, 2)\n',

            'from {imp} import error\n\n'
            'raise OSError(1, 2)\n',
        ),
        (
            'from {imp} import error\n\n'
            'raise error(\n'
            '    1,\n'
            '    2,\n'
            ')',

            'from {imp} import error\n\n'
            'raise OSError(\n'
            '    1,\n'
            '    2,\n'
            ')',
        ),
    ),
)
def test_fix_oserror_complex_aliases_raise(imp, tpl, expected_tpl):
    s, expected = tpl.format(imp=imp), expected_tpl.format(imp=imp)
    assert _fix_py3_plus(s) == expected
