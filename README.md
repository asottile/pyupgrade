[![Build Status](https://travis-ci.org/asottile/pyupgrade.svg?branch=master)](https://travis-ci.org/asottile/pyupgrade)
[![Coverage Status](https://coveralls.io/repos/github/asottile/pyupgrade/badge.svg?branch=master)](https://coveralls.io/github/asottile/pyupgrade?branch=master)
[![Build status](https://ci.appveyor.com/api/projects/status/tibypnuyu1svqely/branch/master?svg=true)](https://ci.appveyor.com/project/asottile/pyupgrade/branch/master)

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
    rev: v1.11.1
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
dict((a, b) for a, b in y)   # {a: b for a, b in y}
dict([(a, b) for a, b in y)  # {a: b for a, b in y}
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

# note: pyupgrade is timid in one case (that's usually a mistake)
# in python2.x `'\u2603'` is the same as `'\\u2603'` without `unicode_literals`
# but in python3.x, that's our friend ☃
```

### Long literals

Availability:
- If `pyupgrade` is running in python 2.

```python
5L                            # 5
5l                            # 5
123456789123456789123456789L  # 123456789123456789123456789
```

### Octal literals

Availability:
- If `pyupgrade` is running in python 2.
```
0755  # 0o755
05    # 5
```

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

isinstance(..., six.class_types)    # isinstance(..., type)
issubclass(..., six.integer_types)  # issubclass(..., int)
isinstance(..., six.string_types)   # isinstance(..., str)

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

_note_: this is a work-in-progress, see [#59][issue-59].

[issue-59]: https://github.com/asottile/pyupgrade/issues/59

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
