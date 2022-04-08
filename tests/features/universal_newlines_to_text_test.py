from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'version'),
    (
        pytest.param(
            'import subprocess\n'
            'subprocess.run(["foo"], universal_newlines=True)\n',
            (3,),
            id='not Python3.7+',
        ),
        pytest.param(
            'from foo import run\n'
            'run(["foo"], universal_newlines=True)\n',
            (3, 7),
            id='run imported, but not from subprocess',
        ),
        pytest.param(
            'from subprocess import run\n'
            'run(["foo"], shell=True)\n',
            (3, 7),
            id='universal_newlines not used',
        ),
        pytest.param(
            'import subprocess\n'
            'subprocess.run(\n'
            '   ["foo"],\n'
            '   text=True,\n'
            '   universal_newlines=True\n'
            ')\n',
            (3, 7),
            id='both text and universal_newlines',
        ),
        pytest.param(
            'import subprocess\n'
            'subprocess.run(\n'
            '   ["foo"],\n'
            '   universal_newlines=True,\n'
            '   **kwargs,\n'
            ')\n',
            (3, 7),
            id='both **kwargs and universal_newlines',
        ),
    ),
)
def test_fix_universal_newlines_to_text_noop(s, version):
    assert _fix_plugins(s, settings=Settings(min_version=version)) == s


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'import subprocess\n'
            'subprocess.run(["foo"], universal_newlines=True)\n',

            'import subprocess\n'
            'subprocess.run(["foo"], text=True)\n',

            id='subprocess.run attribute',
        ),
        pytest.param(
            'import subprocess\n'
            'subprocess.check_output(["foo"], universal_newlines=True)\n',

            'import subprocess\n'
            'subprocess.check_output(["foo"], text=True)\n',

            id='subprocess.check_output attribute',
        ),
        pytest.param(
            'from subprocess import run\n'
            'run(["foo"], universal_newlines=True)\n',

            'from subprocess import run\n'
            'run(["foo"], text=True)\n',

            id='run imported from subprocess',
        ),
        pytest.param(
            'from subprocess import run\n'
            'run(["foo"], universal_newlines=universal_newlines)\n',

            'from subprocess import run\n'
            'run(["foo"], text=universal_newlines)\n',

            id='universal_newlines appears as value',
        ),
        pytest.param(
            'from subprocess import run\n'
            'run(["foo"], *foo, universal_newlines=universal_newlines)\n',

            'from subprocess import run\n'
            'run(["foo"], *foo, text=universal_newlines)\n',

            id='with starargs',
        ),
    ),
)
def test_fix_universal_newlines_to_text(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 7)))
    assert ret == expected
