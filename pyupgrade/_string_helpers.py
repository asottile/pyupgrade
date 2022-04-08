from __future__ import annotations

import codecs
import re
import string
from typing import Optional
from typing import Tuple

NAMED_UNICODE_RE = re.compile(r'(?<!\\)(?:\\\\)*(\\N\{[^}]+\})')

DotFormatPart = Tuple[str, Optional[str], Optional[str], Optional[str]]

_stdlib_parse_format = string.Formatter().parse


def parse_format(s: str) -> list[DotFormatPart]:
    """handle named escape sequences"""
    ret: list[DotFormatPart] = []

    for part in NAMED_UNICODE_RE.split(s):
        if NAMED_UNICODE_RE.fullmatch(part):
            if not ret:
                ret.append((part, None, None, None))
            else:
                ret[-1] = (ret[-1][0] + part, None, None, None)
        else:
            first = True
            for tup in _stdlib_parse_format(part):
                if not first or not ret:
                    ret.append(tup)
                else:
                    ret[-1] = (ret[-1][0] + tup[0], *tup[1:])
                first = False

    if not ret:
        ret.append((s, None, None, None))

    return ret


def unparse_parsed_string(parsed: list[DotFormatPart]) -> str:
    def _convert_tup(tup: DotFormatPart) -> str:
        ret, field_name, format_spec, conversion = tup
        ret = curly_escape(ret)
        if field_name is not None:
            ret += '{' + field_name
            if conversion:
                ret += '!' + conversion
            if format_spec:
                ret += ':' + format_spec
            ret += '}'
        return ret

    return ''.join(_convert_tup(tup) for tup in parsed)


def curly_escape(s: str) -> str:
    parts = NAMED_UNICODE_RE.split(s)
    return ''.join(
        part.replace('{', '{{').replace('}', '}}')
        if not NAMED_UNICODE_RE.fullmatch(part)
        else part
        for part in parts
    )


def is_codec(encoding: str, name: str) -> bool:
    try:
        return codecs.lookup(encoding).name == name
    except LookupError:
        return False
