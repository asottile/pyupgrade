from __future__ import annotations

import pytest

from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'min_version'),
    (
        pytest.param('from a import b', (3,), id='unrelated import'),
        pytest.param(
            'from .xml.etree.cElementTree import XML\n',
            (3,),
            id='leave relative imports alone',
        ),
        pytest.param(
            'if True: from six.moves import getcwd, StringIO\n',
            (3,),
            id='inline from-import with space',
        ),
        pytest.param(
            'if True:from six.moves import getcwd, StringIO\n',
            (3,),
            id='inline from-import without space',
        ),
        pytest.param(
            'if True:import mock, sys\n',
            (3,),
            id='inline import-import',
        ),
        pytest.param(
            'import xml.etree.cElementTree',
            (3,),
            id='import without alias',
        ),
        pytest.param(
            'from xml.etree import cElementTree',
            (3,),
            id='from import of module without alias',
        ),
        pytest.param(
            'from typing import Callable\n',
            (3, 9),
            id='skip rewriting of Callable in 3.9 since it is broken',
        ),
    ),
)
def test_import_replaces_noop(s, min_version):
    assert _fix_plugins(s, settings=Settings(min_version=min_version)) == s


def test_mock_noop_keep_mock():
    """This would've been rewritten if keep_mock were False"""
    s = (
        'from mock import patch\n'
        '\n'
        'patch("func")'
    )
    settings = Settings(keep_mock=True)
    assert _fix_plugins(s, settings=settings) == s


@pytest.mark.parametrize(
    ('s', 'min_version', 'expected'),
    (
        pytest.param(
            'from collections import Mapping\n',
            (3,),
            'from collections.abc import Mapping\n',
            id='one-name replacement',
        ),
        pytest.param(
            'from collections import Mapping as MAP\n',
            (3,),
            'from collections.abc import Mapping as MAP\n',
            id='one-name replacement with alias',
        ),
        pytest.param(
            'from collections import Mapping, Sequence\n',
            (3,),
            'from collections.abc import Mapping, Sequence\n',
            id='multi-name replacement',
        ),
        pytest.param(
            'from collections import Counter, Mapping\n',
            (3,),
            'from collections import Counter\n'
            'from collections.abc import Mapping\n',
            id='one name rewritten to new module',
        ),
        pytest.param(
            'from collections import Counter, Mapping',
            (3,),
            'from collections import Counter\n'
            'from collections.abc import Mapping\n',
            id='one name rewritten to new module, no eol',
        ),
        pytest.param(
            'from collections import (Counter, \n'
            '                         Mapping)\n',
            (3,),
            'from collections import (Counter)\n'
            'from collections.abc import Mapping\n',
            id='one name rewritten with parens',
        ),
        pytest.param(
            'from collections import Counter, \\\n'
            '                         Mapping\n',
            (3,),
            'from collections import Counter\n'
            'from collections.abc import Mapping\n',
            id='one name rewritten with backslash',
        ),
        pytest.param(
            'from collections import Counter, Mapping, Sequence\n',
            (3,),
            'from collections import Counter\n'
            'from collections.abc import Mapping, Sequence\n',
            id='multiple names rewritten to new module',
        ),
        pytest.param(
            'from six.moves import getcwd, StringIO\n',
            (3,),
            'from io import StringIO\n'
            'from os import getcwd\n',
            id='all imports rewritten but to multiple modules',
        ),
        pytest.param(
            'from collections import Mapping as mapping, Counter\n',
            (3,),
            'from collections import Counter\n'
            'from collections.abc import Mapping as mapping\n',
            id='new import with aliased name',
        ),
        pytest.param(
            'if True:\n'
            '    from xml.etree import cElementTree as ET\n',
            (3,),
            'if True:\n'
            '    from xml.etree import ElementTree as ET\n',
            id='indented and full import replaced',
        ),
        pytest.param(
            'if True:\n'
            '    from collections import Mapping, Counter\n',
            (3,),
            'if True:\n'
            '    from collections import Counter\n'
            '    from collections.abc import Mapping\n',
            id='indented from-import being added',
        ),
        pytest.param(
            'if True:\n'
            '    from six.moves import queue, urllib_request\n',
            (3,),
            'if True:\n'
            '    from six.moves import urllib_request\n'
            '    import queue\n',
            id='indented import-import being added',
        ),
        pytest.param(
            'if True:\n'
            '    import mock\n',
            (3,),
            'if True:\n'
            '    from unittest import mock\n',
            id='indented import-import rewritten',
        ),
        pytest.param(
            'if True:\n'
            '    if True:\n'
            '        pass\n'
            '    from collections import Mapping, Counter\n',
            (3,),
            'if True:\n'
            '    if True:\n'
            '        pass\n'
            '    from collections import Counter\n'
            '    from collections.abc import Mapping\n',
            id='indented import after dedent',
        ),
        pytest.param(
            'if True: from collections import Mapping\n',
            (3,),
            'if True: from collections.abc import Mapping\n',
            id='inline import, only one replacement',
        ),
        pytest.param(
            'import os\n'
            'from collections import Counter, Mapping\n'
            'import sys\n',
            (3,),
            'import os\n'
            'from collections import Counter\n'
            'from collections.abc import Mapping\n'
            'import sys\n',
            id='other imports left alone',
        ),
        pytest.param(
            'from six.moves import urllib_request, filter, getcwd\n',
            (3,),
            'from six.moves import urllib_request\n'
            'from os import getcwd\n',
            id='replaces and removals and one remaining',
        ),
        pytest.param(
            'from six.moves import filter, getcwd\n',
            (3,),
            'from os import getcwd\n',
            id='replaces and removals and no remaining',
        ),
        pytest.param(
            'from six.moves.queue import Queue\n',
            (3,),
            'from queue import Queue\n',
            id='module replacement',
        ),
        pytest.param(
            'from xml.etree.cElementTree import XML\n',
            (3,),
            'from xml.etree.ElementTree import XML\n',
            id='relative import func',
        ),
        pytest.param(
            'from xml.etree.cElementTree import XML, Element\n',
            (3,),
            'from xml.etree.ElementTree import XML, Element\n',
            id='import multiple objects',
        ),
        pytest.param(
            'from six.moves import queue\n',
            (3,),
            'import queue\n',
            id='from import a module to an import-import',
        ),
        pytest.param(
            'from six.moves import queue, map, getcwd\n',
            (3,),
            'from os import getcwd\n'
            'import queue\n',
            id='removal, rename, module rename',
        ),
        pytest.param(
            'from xml.etree import cElementTree as ET\n',
            (3,),
            'from xml.etree import ElementTree as ET\n',
            id='from import a module but aliased',
        ),
        pytest.param(
            'import xml.etree.cElementTree as ET',
            (3,),
            'import xml.etree.ElementTree as ET',
            id='import with alias',
        ),
        pytest.param(
            'import contextlib, xml.etree.cElementTree as ET\n',
            (3,),
            'import contextlib, xml.etree.ElementTree as ET\n',
            id='can rewrite multiple import imports',
        ),
        pytest.param(
            'import mock\n',
            (3,),
            'from unittest import mock\n',
            id='rewrites mock import',
        ),
        pytest.param(
            'import mock.mock\n',
            (3,),
            'from unittest import mock\n',
            id='rewrites mock.mock import',
        ),
        pytest.param(
            'import contextlib, mock, sys\n',
            (3,),
            'import contextlib, sys\n'
            'from unittest import mock\n',
            id='mock rewriting multiple imports in middle',
        ),
        pytest.param(
            'import mock, sys\n',
            (3,),
            'import sys\n'
            'from unittest import mock\n',
            id='mock rewriting multiple imports at beginning',
        ),
        pytest.param(
            'import mock, sys',
            (3,),
            'import sys\n'
            'from unittest import mock\n',
            id='adds import-import no eol',
        ),
        pytest.param(
            'from mock import mock\n',
            (3,),
            'from unittest import mock\n',
            id='mock import mock import',
        ),
        pytest.param(
            'from typing import Callable\n',
            (3, 10),
            'from collections.abc import Callable\n',
            id='typing.Callable is rewritable in 3.10+ only',
        ),
        pytest.param(
            'from typing import Optional, Sequence as S\n',
            (3, 10),
            'from typing import Optional\n'
            'from collections.abc import Sequence as S\n',
            id='aliasing in multi from import',
        ),
    ),
)
def test_import_replaces(s, min_version, expected):
    ret = _fix_plugins(s, settings=Settings(min_version=min_version))
    assert ret == expected
