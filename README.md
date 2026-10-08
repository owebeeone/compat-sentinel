# compat-sentinel

PEP 661 `sentinel` for Python 3.10 and later.

On Python 3.15 and later, `compat_sentinel.sentinel` is the builtin. On older
interpreters it is a local implementation with the same constructor, copy
behavior, and pickle lookup.

```python
from compat_sentinel import sentinel

MISSING = sentinel("MISSING")
DEFAULT = sentinel("DEFAULT", repr="<default>")
```

Each call returns a new object. A sentinel pickles back to itself when it can
be imported from its module under `__name__`:

```python
MISSING = sentinel("MISSING")

class Box:
    SHORT = sentinel("Box.SHORT")
```

A sentinel created in a local scope and never stored under that name does not
pickle. `__module__` is taken from the caller and is writable; pickle uses the
value present at dump time.

`int | MISSING` and `MISSING | str` build a `typing.Union`.
