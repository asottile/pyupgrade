import string
import sys

if sys.version_info >= (3, 7):  # pragma: no cover (py37+)
    is_ascii = str.isascii
else:  # pragma: no cover (<py37)
    def is_ascii(s: str) -> bool:
        return all(c in string.printable for c in s)
