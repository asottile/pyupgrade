# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pyupgrade import _is_bytestring


@pytest.mark.parametrize('s', ("b''", 'b""', 'B""', "B''", "rb''", "rb''"))
def test_is_bytestring_true(s):
    assert _is_bytestring(s) is True


@pytest.mark.parametrize('s', ('', '""', "''", 'u""', '"b"'))
def test_is_bytestring_false(s):
    assert _is_bytestring(s) is False
