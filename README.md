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
    sha: v1.4.0
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
'%(a)s %(b)s' % {'a': 1, 'b': 2}  # '{a} {b}'.format(a=1, b2=)
```

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
