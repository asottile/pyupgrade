import pytest

from pyupgrade import _fix_py3_plus


@pytest.mark.parametrize(
    ('s', 'min_version'),
    (
        pytest.param(
            'from dataclasses import dataclass as dataclass2\n\n'
            '@dataclass2()\n'
            'def foo():\n'
            '    pass\n',
            (3, 7),
            id='not following as imports',
        ),
        pytest.param(
            'from dataclasses import dataclass\n\n'
            '@dataclass(eq=False)\n'
            'def foo():\n'
            '    pass\n',
            (3, 7),
            id='not rewriting calls with args',
        ),
        pytest.param(
            'from dataclasses2 import dataclass\n\n'
            '@dataclass()\n'
            'def foo():\n'
            '    pass\n',
            (3, 7),
            id='not following unknown import',
        ),
        pytest.param(
            'from dataclasses import dataclass\n\n'
            '@dataclass()\n'
            'def foo():\n'
            '    pass\n',
            (3,),
            id='not rewriting below 3.7',
        ),
        pytest.param(
            'from .dataclasses import dataclass\n'
            '@dataclass()\n'
            'def foo(): pass\n',
            (3, 7),
            id='relative imports',
        ),
    ),
)
def test_fix_dataclasses_dataclass_noop(s, min_version):
    assert _fix_py3_plus(s, min_version) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from dataclasses import dataclass\n\n'
            '@dataclass()\n'
            'def foo():\n'
            '    pass\n',
            'from dataclasses import dataclass\n\n'
            '@dataclass\n'
            'def foo():\n'
            '    pass\n',
            id='call without attr',
        ),
        pytest.param(
            'import dataclasses\n\n'
            '@dataclasses.dataclass()\n'
            'def foo():\n'
            '    pass\n',
            'import dataclasses\n\n'
            '@dataclasses.dataclass\n'
            'def foo():\n'
            '    pass\n',
            id='call with attr',
        ),
    ),
)
def test_fix_dataclasses_dataclass(s, expected):
    assert _fix_py3_plus(s, (3, 7)) == expected
