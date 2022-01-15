from __future__ import annotations

import codecs
import re

NAMED_UNICODE_RE = re.compile(r'(?<!\\)(?:\\\\)*(\\N\{[^}]+\})')


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
