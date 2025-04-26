from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.xfail
@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            "from typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING:\n"
            "    from typing import Protocol\n"
            "else:\n"
            "    Protocol = object\n",
            "from typing import TYPE_CHECKING\n\n"
            "from typing import Protocol\n",
            id="import of Protocol",
        ),
    ),
)
def test_remove_type_checking_block_for_protocol(s, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=(3, 8)))
    assert ret == expected
