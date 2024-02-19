[![build status](https://github.com/asottile/pyupgrade/actions/workflows/main.yml/badge.svg)](https://github.com/asottile/pyupgrade/actions/workflows/main.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/asottile/pyupgrade/main.svg)](https://results.pre-commit.ci/latest/github/asottile/pyupgrade/main)

pyupgrade
=========

A tool (and pre-commit hook) to automatically upgrade syntax for newer
versions of the language.

## Installation

```bash
pip install pyupgrade
```

## As a pre-commit hook

See [pre-commit](https://github.com/pre-commit/pre-commit) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/asottile/pyupgrade
    rev: v3.15.1
    hooks:
    -   id: pyupgrade
```

## Implemented features

### Set literals

```diff
-set(())
+set()
-set([])
+set()
-set((1,))
+{1}
-set((1, 2))
+{1, 2}
-set([1, 2])
+{1, 2}
-set(x for x in y)
+{x for x in y}
-set([x for x in y])
+{x for x in y}
```

### Dictionary comprehensions

```diff
-dict((a, b) for a, b in y)
+{a: b for a, b in y}
-dict([(a, b) for a, b in y])
+{a: b for a, b in y}
```

### Replace unnecessary lambdas in `collections.defaultdict` calls

```diff
-defaultdict(lambda: [])
+defaultdict(list)
-defaultdict(lambda: list())
+defaultdict(list)
-defaultdict(lambda: {})
+defaultdict(dict)
-defaultdict(lambda: dict())
+defaultdict(dict)
-defaultdict(lambda: ())
+defaultdict(tuple)
-defaultdict(lambda: tuple())
+defaultdict(tuple)
-defaultdict(lambda: set())
+defaultdict(set)
-defaultdict(lambda: 0)
+defaultdict(int)
-defaultdict(lambda: 0.0)
+defaultdict(float)
-defaultdict(lambda: 0j)
+defaultdict(complex)
-defaultdict(lambda: '')
+defaultdict(str)
```

### Format Specifiers

```diff
-'{0} {1}'.format(1, 2)
+'{} {}'.format(1, 2)
-'{0}' '{1}'.format(1, 2)
+'{}' '{}'.format(1, 2)
```

### printf-style string formatting

Availability:
- Unless `--keep-percent-format` is passed.

```diff
-'%s %s' % (a, b)
+'{} {}'.format(a, b)
-'%r %2f' % (a, b)
+'{!r} {:2f}'.format(a, b)
-'%(a)s %(b)s' % {'a': 1, 'b': 2}
+'{a} {b}'.format(a=1, b=2)
```

### Unicode literals

```diff
-u'foo'
+'foo'
-u"foo"
+'foo'
-u'''foo'''
+'''foo'''
```

### Invalid escape sequences

```diff
 # strings with only invalid sequences become raw strings
-'\d'
+r'\d'
 # strings with mixed valid / invalid sequences get escaped
-'\n\d'
+'\n\\d'
-u'\d'
+r'\d'
 # this fixes a syntax error in python3.3+
-'\N'
+r'\N'
```

### `is` / `is not` comparison to constant literals

In python3.8+, comparison to literals becomes a `SyntaxWarning` as the success
of those comparisons is implementation specific (due to common object caching).

```diff
-x is 5
+x == 5
-x is not 5
+x != 5
-x is 'foo'
+x == 'foo'
```

### `.encode()` to bytes literals

```diff
-'foo'.encode()
+b'foo'
-'foo'.encode('ascii')
+b'foo'
-'foo'.encode('utf-8')
+b'foo'
-u'foo'.encode()
+b'foo'
-'\xa0'.encode('latin1')
+b'\xa0'
```

### extraneous parens in `print(...)`

A fix for [python-modernize/python-modernize#178]

```diff
 # ok: printing an empty tuple
 print(())
 # ok: printing a tuple
 print((1,))
 # ok: parenthesized generator argument
 sum((i for i in range(3)), [])
 # fixed:
-print(("foo"))
+print("foo")
```

[python-modernize/python-modernize#178]: https://github.com/python-modernize/python-modernize/issues/178

### constant fold `isinstance` / `issubclass` / `except`

```diff
-isinstance(x, (int, int))
+isinstance(x, int)

-issubclass(y, (str, str))
+issubclass(y, str)

 try:
     raises()
-except (Error1, Error1, Error2):
+except (Error1, Error2):
     pass
```

### unittest deprecated aliases

Rewrites [deprecated unittest method aliases](https://docs.python.org/3/library/unittest.html#deprecated-aliases) to their non-deprecated forms.

```diff
 from unittest import TestCase


 class MyTests(TestCase):
     def test_something(self):
-        self.failUnlessEqual(1, 1)
+        self.assertEqual(1, 1)
-        self.assertEquals(1, 1)
+        self.assertEqual(1, 1)
```

### `super()` calls

```diff
 class C(Base):
     def f(self):
-        super(C, self).f()
+        super().f()
```

### "new style" classes

#### rewrites class declaration

```diff
-class C(object): pass
+class C: pass
-class C(B, object): pass
+class C(B): pass
```

#### removes `__metaclass__ = type` declaration

```diff
 class C:
-    __metaclass__ = type
```

### forced `str("native")` literals

```diff
-str()
+''
-str("foo")
+"foo"
```

### `.encode("utf-8")`

```diff
-"foo".encode("utf-8")
+"foo".encode()
```

### `# coding: ...` comment

as of [PEP 3120], the default encoding for python source is UTF-8

```diff
-# coding: utf-8
 x = 1
```

[PEP 3120]: https://www.python.org/dev/peps/pep-3120/

### `__future__` import removal

Availability:
- by default removes `nested_scopes`, `generators`, `with_statement`,
  `absolute_import`, `division`, `print_function`, `unicode_literals`
- `--py37-plus` will also remove `generator_stop`

```diff
-from __future__ import with_statement
```

### Remove unnecessary py3-compat imports

```diff
-from io import open
-from six.moves import map
-from builtins import object  # python-future
```

### import replacements

Availability:
- `--py36-plus` (and others) will replace imports

see also [reorder-python-imports](https://github.com/asottile/reorder_python_imports#removing--rewriting-obsolete-six-imports)

some examples:

```diff
-from collections import deque, Mapping
+from collections import deque
+from collections.abc import Mapping
```

```diff
-from typing import Sequence
+from collections.abc import Sequence
```

```diff
-from typing_extensions import Concatenate
+from typing import Concatenate
```

### rewrite `mock` imports

Availability:
- [Unless `--keep-mock` is passed on the commandline](https://github.com/asottile/pyupgrade/issues/314).

```diff
-from mock import patch
+from unittest.mock import patch
```

### `yield` => `yield from`

```diff
 def f():
-    for x in y:
-        yield x
+    yield from y
-    for a, b in c:
-        yield (a, b)
+    yield from c
```

### Python2 and old Python3.x blocks

```diff
 import sys
-if sys.version_info < (3,):  # also understands `six.PY2` (and `not`), `six.PY3` (and `not`)
-    print('py2')
-else:
-    print('py3')
+print('py3')
```

Availability:
- `--py36-plus` will remove Python <= 3.5 only blocks
- `--py37-plus` will remove Python <= 3.6 only blocks
- so on and so forth

```diff
 # using --py36-plus for this example

 import sys
-if sys.version_info < (3, 6):
-    print('py3.5')
-else:
-    print('py3.6+')
+print('py3.6+')

-if sys.version_info <= (3, 5):
-    print('py3.5')
-else:
-    print('py3.6+')
+print('py3.6+')

-if sys.version_info >= (3, 6):
-    print('py3.6+')
-else:
-    print('py3.5')
+print('py3.6+')
```

Note that `if` blocks without an `else` will not be rewritten as it could introduce a syntax error.

### remove `six` compatibility code

```diff
-six.text_type
+str
-six.binary_type
+bytes
-six.class_types
+(type,)
-six.string_types
+(str,)
-six.integer_types
+(int,)
-six.unichr
+chr
-six.iterbytes
+iter
-six.print_(...)
+print(...)
-six.exec_(c, g, l)
+exec(c, g, l)
-six.advance_iterator(it)
+next(it)
-six.next(it)
+next(it)
-six.callable(x)
+callable(x)
-six.moves.range(x)
+range(x)
-six.moves.xrange(x)
+range(x)


-from six import text_type
-text_type
+str

-@six.python_2_unicode_compatible
 class C:
     def __str__(self):
         return u'C()'

-class C(six.Iterator): pass
+class C: pass

-class C(six.with_metaclass(M, B)): pass
+class C(B, metaclass=M): pass

-@six.add_metaclass(M)
-class C(B): pass
+class C(B, metaclass=M): pass

-isinstance(..., six.class_types)
+isinstance(..., type)
-issubclass(..., six.integer_types)
+issubclass(..., int)
-isinstance(..., six.string_types)
+isinstance(..., str)

-six.b('...')
+b'...'
-six.u('...')
+'...'
-six.byte2int(bs)
+bs[0]
-six.indexbytes(bs, i)
+bs[i]
-six.int2byte(i)
+bytes((i,))
-six.iteritems(dct)
+dct.items()
-six.iterkeys(dct)
+dct.keys()
-six.itervalues(dct)
+dct.values()
-next(six.iteritems(dct))
+next(iter(dct.items()))
-next(six.iterkeys(dct))
+next(iter(dct.keys()))
-next(six.itervalues(dct))
+next(iter(dct.values()))
-six.viewitems(dct)
+dct.items()
-six.viewkeys(dct)
+dct.keys()
-six.viewvalues(dct)
+dct.values()
-six.create_unbound_method(fn, cls)
+fn
-six.get_unbound_function(meth)
+meth
-six.get_method_function(meth)
+meth.__func__
-six.get_method_self(meth)
+meth.__self__
-six.get_function_closure(fn)
+fn.__closure__
-six.get_function_code(fn)
+fn.__code__
-six.get_function_defaults(fn)
+fn.__defaults__
-six.get_function_globals(fn)
+fn.__globals__
-six.raise_from(exc, exc_from)
+raise exc from exc_from
-six.reraise(tp, exc, tb)
+raise exc.with_traceback(tb)
-six.reraise(*sys.exc_info())
+raise
-six.assertCountEqual(self, a1, a2)
+self.assertCountEqual(a1, a2)
-six.assertRaisesRegex(self, e, r, fn)
+self.assertRaisesRegex(e, r, fn)
-six.assertRegex(self, s, r)
+self.assertRegex(s, r)

 # note: only for *literals*
-six.ensure_binary('...')
+b'...'
-six.ensure_str('...')
+'...'
-six.ensure_text('...')
+'...'
```

### `open` alias

```diff
-with io.open('f.txt') as f:
+with open('f.txt') as f:
     ...
```


### redundant `open` modes

```diff
-open("foo", "U")
+open("foo")
-open("foo", "Ur")
+open("foo")
-open("foo", "Ub")
+open("foo", "rb")
-open("foo", "rUb")
+open("foo", "rb")
-open("foo", "r")
+open("foo")
-open("foo", "rt")
+open("foo")
-open("f", "r", encoding="UTF-8")
+open("f", encoding="UTF-8")
-open("f", "wt")
+open("f", "w")
```


### `OSError` aliases

```diff
 # also understands:
 # - IOError
 # - WindowsError
 # - mmap.error and uses of `from mmap import error`
 # - select.error and uses of `from select import error`
 # - socket.error and uses of `from socket import error`

 def throw():
-    raise EnvironmentError('boom')
+    raise OSError('boom')

 def catch():
     try:
         throw()
-    except EnvironmentError:
+    except OSError:
         handle_error()
```

### `TimeoutError` aliases

Availability:
- `--py310-plus` for `socket.timeout`
- `--py311-plus` for `asyncio.TimeoutError`

```diff

 def throw(a):
     if a:
-        raise asyncio.TimeoutError('boom')
+        raise TimeoutError('boom')
     else:
-        raise socket.timeout('boom')
+        raise TimeoutError('boom')

 def catch(a):
     try:
         throw(a)
-    except (asyncio.TimeoutError, socket.timeout):
+    except TimeoutError:
         handle_error()
```

### `typing.Text` str alias

```diff
-def f(x: Text) -> None:
+def f(x: str) -> None:
     ...
```


### Unpacking list comprehensions

```diff
-foo, bar, baz = [fn(x) for x in items]
+foo, bar, baz = (fn(x) for x in items)
```


### Rewrite `xml.etree.cElementTree` to `xml.etree.ElementTree`

```diff
-import xml.etree.cElementTree as ET
+import xml.etree.ElementTree as ET
-from xml.etree.cElementTree import XML
+from xml.etree.ElementTree import XML
```


### Rewrite `type` of primitive

```diff
-type('')
+str
-type(b'')
+bytes
-type(0)
+int
-type(0.)
+float
```

### `typing.NamedTuple` / `typing.TypedDict` py36+ syntax

Availability:
- `--py36-plus` is passed on the commandline.

```diff
-NT = typing.NamedTuple('NT', [('a', int), ('b', Tuple[str, ...])])
+class NT(typing.NamedTuple):
+    a: int
+    b: Tuple[str, ...]

-D1 = typing.TypedDict('D1', a=int, b=str)
+class D1(typing.TypedDict):
+    a: int
+    b: str

-D2 = typing.TypedDict('D2', {'a': int, 'b': str})
+class D2(typing.TypedDict):
+    a: int
+    b: str
```

### f-strings

Availability:
- `--py36-plus` is passed on the commandline.

```diff
-'{foo} {bar}'.format(foo=foo, bar=bar)
+f'{foo} {bar}'
-'{} {}'.format(foo, bar)
+f'{foo} {bar}'
-'{} {}'.format(foo.bar, baz.womp)
+f'{foo.bar} {baz.womp}'
-'{} {}'.format(f(), g())
+f'{f()} {g()}'
-'{x}'.format(**locals())
+f'{x}'
```

_note_: `pyupgrade` is intentionally timid and will not create an f-string
if it would make the expression longer or if the substitution parameters are
sufficiently complicated (as this can decrease readability).


### `subprocess.run`: replace `universal_newlines` with `text`

Availability:
- `--py37-plus` is passed on the commandline.

```diff
-output = subprocess.run(['foo'], universal_newlines=True)
+output = subprocess.run(['foo'], text=True)
```


### `subprocess.run`: replace `stdout=subprocess.PIPE, stderr=subprocess.PIPE` with `capture_output=True`

Availability:
- `--py37-plus` is passed on the commandline.

```diff
-output = subprocess.run(['foo'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
+output = subprocess.run(['foo'], capture_output=True)
```


### remove parentheses from `@functools.lru_cache()`

Availability:
- `--py38-plus` is passed on the commandline.

```diff
 import functools

-@functools.lru_cache()
+@functools.lru_cache
 def expensive():
     ...
```

### shlex.join

Availability:
- `--py38-plus` is passed on the commandline.

```diff
-' '.join(shlex.quote(arg) for arg in cmd)
+shlex.join(cmd)
```

### replace `@functools.lru_cache(maxsize=None)` with shorthand

Availability:
- `--py39-plus` is passed on the commandline.

```diff
 import functools

-@functools.lru_cache(maxsize=None)
+@functools.cache
 def expensive():
     ...
```


### pep 585 typing rewrites

Availability:
- File imports `from __future__ import annotations`
    - Unless `--keep-runtime-typing` is passed on the commandline.
- `--py39-plus` is passed on the commandline.

```diff
-def f(x: List[str]) -> None:
+def f(x: list[str]) -> None:
     ...
```


### pep 604 typing rewrites

Availability:
- File imports `from __future__ import annotations`
    - Unless `--keep-runtime-typing` is passed on the commandline.
- `--py310-plus` is passed on the commandline.

```diff
-def f() -> Optional[str]:
+def f() -> str | None:
     ...
```

```diff
-def f() -> Union[int, str]:
+def f() -> int | str:
     ...
```


### remove quoted annotations

Availability:
- File imports `from __future__ import annotations`

```diff
-def f(x: 'queue.Queue[int]') -> C:
+def f(x: queue.Queue[int]) -> C:
```


### use `datetime.UTC` alias

Availability:
- `--py311-plus` is passed on the commandline.

```diff
 import datetime

-datetime.timezone.utc
+datetime.UTC
```
