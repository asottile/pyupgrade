pyupgrade
=========

A tool (and pre-commit hook) to automatically upgrade syntax for newer
versions of the language.

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

### Python2.7+ Format Specifiers

```python
'{0} {1}'.format(1, 2)  # '{} {}'.format(1, 2)
```


## Planned features

### Dictionary comprehensions

```python
dict((a, b) for a, b in y)   # {a: b for a, b in y}
dict([(a, b) for a, b in y)  # {a: b for a, b in y}
```

### Unicode literals

Availability:
- File imports `from __future__ import unicode_literals`
- `--py3-plus` is passed on the commandline.

```python
u'foo'      # 'foo'
U'foo'      # 'foo'
u"foo"      # 'foo'
U"foo"      # 'foo'
u'''foo'''  # '''foo'''
```

### f-strings

Availability:
- `--py36-plus` is passed on the commandline.

```python
'{foo} {bar}'.format(foo=foo, bar=bar)  # f'{foo} {bar}'
'{} {}'.format(foo, bar)                # f'{foo} {bar}'
```
