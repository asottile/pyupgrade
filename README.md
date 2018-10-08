[![Build Status](https://travis-ci.org/vmarkovtsev/pyupgrade-opt.svg?branch=master)](https://travis-ci.org/vmarkovtsev/pyupgrade-opt)
[![Coverage Status](https://coveralls.io/repos/github/vmarkovtsev/pyupgrade-opt/badge.svg?branch=master)](https://coveralls.io/github/vmarkovtsev/pyupgrade-opt?branch=master)
[![Build status](https://ci.appveyor.com/api/projects/status/ts09kyr3ahprg3q9/branch/master?svg=true)](https://ci.appveyor.com/project/vmarkovtsev/pyupgrade-opt/branch/master)

pyupgrade-opt
=============

A tool (and pre-commit hook) to automatically upgrade syntax for newer
versions of the Python language.
This is actually a fork of [asottile/pyupgrade](https://github.com/asottile/pyupgrade) with the only
difference is that the other maintainer is less opinionated and accepts changes which would never
be accepted in the original project. For example, `--no-percent` disables turning `%` string
formatting into `format()` calls. Upstream changes are manually mirrored from time to time;
please file an issue if there is a sync lag.

## Installation

`pip install pyupgrade-opt`


## As a pre-commit hook

See [pre-commit](https://github.com/pre-commit/pre-commit) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/vmarkovtsev/pyupgrade-opt
    rev: v1.7.0
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

```python
'%s %s' % (a, b)                  # '{} {}'.format(a, b)
'%r %2f' % (a, b)                 # '{!r} {:2f}'.format(a, b)
'%(a)s %(b)s' % {'a': 1, 'b': 2}  # '{a} {b}'.format(a=1, b=2)
```

Can be disabled with `--no-percent` command line argument.

Key format (`%(key)s`) rewriting is planned but not yet implemented.

### Unicode literals

Availability:
- File imports `from __future__ import unicode_literals`
- `--py3-plus` is passed on the commandline.

```python
u'foo'      # 'foo'
u"foo"      # 'foo'
u'''foo'''  # '''foo'''
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
```

_note_: this is a work-in-progress, see #59.

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
