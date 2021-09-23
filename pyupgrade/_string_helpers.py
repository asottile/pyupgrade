import codecs
import re
import string
import sys

if sys.version_info >= (3, 7):  # pragma: no cover (py37+)
    is_ascii = str.isascii
else:  # pragma: no cover (<py37)
    def is_ascii(s: str) -> bool:
        return all(c in string.printable for c in s)

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
