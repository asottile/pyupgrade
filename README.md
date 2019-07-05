[![Build Status](https://dev.azure.com/asottile/asottile/_apis/build/status/asottile.pyupgrade?branchName=master)](https://dev.azure.com/asottile/asottile/_build/latest?definitionId=2&branchName=master)
[![Azure DevOps coverage](https://img.shields.io/azure-devops/coverage/asottile/asottile/2/master.svg)](https://dev.azure.com/asottile/asottile/_build/latest?definitionId=2&branchName=master)

pyupgrade
=========

A tool (and pre-commit hook) to automatically upgrade syntax for newer
versions of the language.

## Installation

`pip install pyupgrade`

## As a pre-commit hook

See [pre-commit](https://github.com/pre-commit/pre-commit) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/asottile/pyupgrade
    rev: v1.20.0
    hooks:
    -   id: pyupgrade
```

## Implemented features

### Set literals

```python
set(())              # set()
set([])              # set()
set((1,))            # {1}
set((1, 2))          # {1, 2}
set([1, 2])          # {1, 2}
set(x for x in y)    # {x for x in y}
set([x for x in y])  # {x for x in y}
```

### Dictionary comprehensions

```python
dict((a, b) for a, b in y)    # {a: b for a, b in y}
dict([(a, b) for a, b in y])  # {a: b for a, b in y}
```

### Python2.7+ Format Specifiers

```python
'{0} {1}'.format(1, 2)    # '{} {}'.format(1, 2)
'{0}' '{1}'.format(1, 2)  # '{}' '{}'.format(1, 2)
```

### printf-style string formatting

Availability:
- Unless `--keep-percent-format` is passed.

```python
'%s %s' % (a, b)                  # '{} {}'.format(a, b)
'%r %2f' % (a, b)                 # '{!r} {:2f}'.format(a, b)
'%(a)s %(b)s' % {'a': 1, 'b': 2}  # '{a} {b}'.format(a=1, b=2)
```

### Unicode literals

Availability:
- File imports `from __future__ import unicode_literals`
- `--py3-plus` is passed on the commandline.

```python
u'foo'      # 'foo'
u"foo"      # 'foo'
u'''foo'''  # '''foo'''
```

### Invalid escape sequences

```python
# strings with only invalid sequences become raw strings
'\d'    # r'\d'
# strings with mixed valid / invalid sequences get escaped
'\n\d'  # '\n\\d'
# `ur` is not a valid string prefix in python3
u'\d'   # u'\\d'

# this fixes a syntax error in python3.3+
'\N'    # r'\N'

# note: pyupgrade is timid in one case (that's usually a mistake)
# in python2.x `'\u2603'` is the same as `'\\u2603'` without `unicode_literals`
# but in python3.x, that's our friend ☃
```

### `is` / `is not` comparison to constant literals

In python3.8+, comparison to literals becomes a `SyntaxWarning` as the success
of those comparisons is implementation specific (due to common object caching).

```python
x is 5      # x == 5
x is not 5  # x != 5
x is 'foo'  # x == foo
```

### `ur` string literals

`ur'...'` literals are not valid in python 3.x

```python
ur'foo'         # u'foo'
ur'\s'          # u'\\s'
# unicode escapes are left alone
ur'\u2603'      # u'\u2603'
ur'\U0001f643'  # u'\U0001f643'
```

### Long literals

```python
5L                            # 5
5l                            # 5
123456789123456789123456789L  # 123456789123456789123456789
```

### Octal literals

```
0755  # 0o755
05    # 5
```

### extraneous parens in `print(...)`

A fix for [python-modernize/python-modernize#178]

```python
print(())                       # ok: printing an empty tuple
print((1,))                     # ok: printing a tuple
sum((i for i in range(3)), [])  # ok: parenthesized generator argument
print(("foo"))                  # print("foo")
```

[python-modernize/python-modernize#178]: https://github.com/python-modernize/python-modernize/issues/178

### `super()` calls

Availability:
- `--py3-plus` is passed on the commandline.

```python
class C(Base):
    def f(self):
        super(C, self).f()   # super().f()
```

### "new style" classes

Availability:
- `--py3-plus` is passed on the commandline.

```python
class C(object): pass     # class C: pass
class C(B, object): pass  # class C(B): pass
```

### forced `str("native")` literals

Availability:
- `--py3-plus` is passed on the commandline.

```python
str("foo")  # "foo"
```

### `.encode("utf-8")`

Availability:
- `--py3-plus` is passed on the commandline.

```python
"foo".encode("utf-8")  # "foo".encode()
```

### `yield` => `yield from`

Availability:
- `--py3-plus` is passed on the commandline.

```python
def f():
    for x in y:       # yield from y
        yield x

    for a, b in c:    # yield from c
        yield (a, b)
```

### `if PY2` blocks

Availability:
- `--py3-plus` is passed on the commandline.

```python
# input
if six.PY2:      # also understands `six.PY3` and `not` and `sys.version_info`
    print('py2')
else:
    print('py3')
# output
print('py3')
```

### remove `six` compatibility code

Availability:
- `--py3-plus` is passed on the commandline.

```python
six.text_type             # str
six.binary_type           # bytes
six.class_types           # (type,)
six.string_types          # (str,)
six.integer_types         # (int,)
six.unichr                # chr
six.iterbytes             # iter
six.print_(...)           # print(...)
six.exec_(c, g, l)        # exec(c, g, l)
six.advance_iterator(it)  # next(it)
six.next(it)              # next(it)
six.callable(x)           # callable(x)

from six import text_type
text_type                 # str

@six.python_2_unicode_compatible  # decorator is removed
class C:
    def __str__(self):
        return u'C()'

class C(six.Iterator): pass              # class C: pass

class C(six.with_metaclass(M, B)): pass  # class C(B, metaclass=M): pass

@six.add_metaclass(M)   # class C(B, metaclass=M): pass
class C(B): pass

isinstance(..., six.class_types)    # isinstance(..., type)
issubclass(..., six.integer_types)  # issubclass(..., int)
isinstance(..., six.string_types)   # isinstance(..., str)

six.b('...')                            # b'...'
six.u('...')                            # '...'
six.byte2int(bs)                        # bs[0]
six.indexbytes(bs, i)                   # bs[i]
six.iteritems(dct)                      # dct.items()
six.iterkeys(dct)                       # dct.keys()
six.itervalues(dct)                     # dct.values()
six.viewitems(dct)                      # dct.items()
six.viewkeys(dct)                       # dct.keys()
six.viewvalues(dct)                     # dct.values()
six.create_unbound_method(fn, cls)      # fn
six.get_unbound_method(meth)            # meth
six.get_method_function(meth)           # meth.__func__
six.get_method_self(meth)               # meth.__self__
six.get_function_closure(fn)            # fn.__closure__
six.get_function_code(fn)               # fn.__code__
six.get_function_defaults(fn)           # fn.__defaults__
six.get_function_globals(fn)            # fn.__globals__
six.assertCountEqual(self, a1, a2)      # self.assertCountEqual(a1, a2)
six.assertRaisesRegex(self, e, r, fn)   # self.assertRaisesRegex(e, r, fn)
six.assertRegex(self, s, r)             # self.assertRegex(s, r)
```

### `OSError` aliases

Availability:
- `--py3-plus` is passed on the commandline.

```python
# input
x = EnvironmentError('boom')        # also understands IOError and WindowsError
raise EnvironmentError('boom')
# output
x = OSError('boom')
raise OSError('boom')
```

### f-strings

Availability:
- `--py36-plus` is passed on the commandline.

```python
'{foo} {bar}'.format(foo=foo, bar=bar)  # f'{foo} {bar}'
'{} {}'.format(foo, bar)                # f'{foo} {bar}'
'{} {}'.format(foo.bar, baz.womp}       # f'{foo.bar} {baz.womp}'
```

_note_: `pyupgrade` is intentionally timid and will not create an f-string
if it would make the expression longer or if the substitution parameters are
anything but simple names or dotted names (as this can decrease readability).
