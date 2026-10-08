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

## pythonbackport-sentinel

[pythonbackport-sentinel](https://github.com/pythonbackport/pythonbackport-sentinel)
0.1.0 claims the same 3.15 `sentinel` contract. Its current `master` does not
meet it. Construction, `repr`, truthiness, identity equality, and copy do work.

- The caller lookup stops on `sentinel.__new__`. Every sentinel reports
  `__module__ == "sentinel.core"` and a qualified name of `sentinel.__new__`.
- Pickle identity is a process-wide registry keyed by that module, that
  qualified name, and the sentinel name. Two `sentinel("MISSING")` values
  share one slot, and the later one replaces the earlier one. Unpickling the
  first returns the second, including in a fresh process after the defining
  module has been imported.
- `__reduce__` rebuilds through a private function. A new process unpickles a
  sentinel without importing the module that defined it, and a custom `repr`
  is dropped. A local sentinel that was never stored under its name still
  pickles.
- Assigning `__module__` changes the attribute and leaves the pickle key
  unchanged.
- `int | sentinel("A")` raises `TypeError` on Python 3.13 because
  `types.UnionType` is not subscriptable. The same subscript is used on every
  version before 3.14. On 3.14 the expression returns a `typing.Union`.
- The package never uses `builtins.sentinel`. On 3.15, `from sentinel import
  sentinel` is still this class, so its pickles are not the builtin
  module-and-name lookup.

`tests/test_contract.py` loads one implementation per run. The default is
`compat_sentinel`. `--sentinel=pybp` loads `pythonbackport-sentinel`. On Python
3.13 the first command passes and the second fails all eight contract checks:

```text
uv run --with pytest pytest -q
uv run --python 3.13 --with pytest --with pythonbackport-sentinel pytest -q --sentinel=pybp tests/test_contract.py
...........................                                                                [100%]
27 passed in 0.18s
FFFFFFFF                                                                                   [100%]
============================================ FAILURES ============================================
___________________________ test_caller_module_is_the_defining_module ____________________________

subjects = <module 'contract_subjects' from '.../contract_subjects.py'>

    def test_caller_module_is_the_defining_module(subjects) -> None:
>       assert subjects.MISSING.__module__ == subjects.__name__
E       AssertionError: assert 'sentinel.core' == 'contract_subjects'
E
E         - contract_subjects
E         + sentinel.core

tests/test_contract.py:71: AssertionError
_________________________ test_same_name_keeps_distinct_pickle_identity __________________________

subjects = <module 'contract_subjects' from '.../contract_subjects.py'>

    def test_same_name_keeps_distinct_pickle_identity(subjects) -> None:
        restored = pickle.loads(pickle.dumps(subjects.MISSING))

>       assert restored is subjects.MISSING
E       AssertionError: assert MISSING is MISSING
E        +  where MISSING = <module 'contract_subjects' from '.../contract_subjects.py'>.MISSING

tests/test_contract.py:77: AssertionError
_________________________________ test_pickle_is_a_module_lookup _________________________________

subjects = <module 'contract_subjects' from '.../contract_subjects.py'>

    def test_pickle_is_a_module_lookup(subjects) -> None:
        blob = pickle.dumps(subjects.MISSING)

>       assert subjects.__name__.encode() in blob
E       AssertionError: assert b'contract_subjects' in b'\x80\x04\x95X\x00\x00\x00\x00\x00\x00\x00\x8c\rsentinel.core\x94\x8c\x15_reconstruct_sentinel\x94\x93\x94\x8c&sentinel.core\x00sentinel.__new__\x00MISSING\x94\x85\x94R\x94.'
E        +  where b'contract_subjects' = <built-in method encode of str object at 0x105f29070>()
E        +    where <built-in method encode of str object at 0x105f29070> = 'contract_subjects'.encode
E        +      where 'contract_subjects' = <module 'contract_subjects' from '.../contract_subjects.py'>.__name__

tests/test_contract.py:84: AssertionError
___________________________ test_custom_repr_survives_in_a_new_process ___________________________

subjects = <module 'contract_subjects' from '.../contract_subjects.py'>

    def test_custom_repr_survives_in_a_new_process(subjects) -> None:
        report = _child("with-module", pickle.dumps(subjects.CUSTOM), subjects)

>       assert report.get("is_custom") == "True", report
E       AssertionError: {'is_custom': 'False', 'repr': 'CUSTOM'}
E       assert 'False' == 'True'
E
E         - True
E         + False

tests/test_contract.py:91: AssertionError
___________________________ test_unpickle_requires_the_defining_module ___________________________

subjects = <module 'contract_subjects' from '.../contract_subjects.py'>

    def test_unpickle_requires_the_defining_module(subjects) -> None:
        report = _child("no-module", pickle.dumps(subjects.MISSING), subjects)

>       assert report.get("error") == "ModuleNotFoundError", report
E       AssertionError: {'ok': 'MISSING', 'module': 'sentinel.core'}
E       assert None == 'ModuleNotFoundError'
E        +  where None = <built-in method get of dict object at 0x105fcc240>('error')
E        +    where <built-in method get of dict object at 0x105fcc240> = {'ok': 'MISSING', 'module': 'sentinel.core'}.get

tests/test_contract.py:98: AssertionError
______________________________ test_local_sentinel_is_not_picklable ______________________________

sentinel = <class 'sentinel.core.sentinel'>

    def test_local_sentinel_is_not_picklable(sentinel) -> None:
        value = sentinel("EPHEMERAL")

>       with pytest.raises(pickle.PicklingError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE PicklingError

tests/test_contract.py:104: Failed
_____________________________ test_module_assignment_controls_pickle _____________________________

subjects = <module 'contract_subjects' from '.../contract_subjects.py'>

    def test_module_assignment_controls_pickle(subjects) -> None:
        original = subjects.HOLDER.__module__
        subjects.HOLDER.__module__ = "not.a.real.module"
        try:
>           with pytest.raises(pickle.PicklingError):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           Failed: DID NOT RAISE PicklingError

tests/test_contract.py:112: Failed
___________________________ test_union_accepts_sentinel_on_either_side ___________________________

sentinel = <class 'sentinel.core.sentinel'>

    def test_union_accepts_sentinel_on_either_side(sentinel) -> None:
        value = sentinel("UNION")
>       forward = int | value
                  ^^^^^^^^^^^

tests/test_contract.py:120:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
site-packages/sentinel/core.py:276: in __ror__
    return _make_union(other, self)
           ^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

a = <class 'int'>, b = UNION

    def _make_union(a, b):
        """
        Build a ``Union`` instance that can be used in type expressions.

        Tries the runtime ``types.UnionType`` (PEP 604, Python 3.10+)
        subscript syntax first, falling back to ``typing.Union``.  Direct
        construction with ``types.UnionType((a, b))`` is intentionally
        avoided because it raises ``TypeError`` on Python 3.14+ where the
        runtime union class is the same as ``typing.Union`` and explicitly
        forbids manual instantiation.
        """
        # On Python 3.10-3.13 ``types.UnionType`` is a distinct class whose
        # subscript syntax (``UnionType[a, b]``) is the supported way of
        # constructing a runtime union.
        union_type = getattr(_types, "UnionType", None)
        if union_type is not None and union_type is not getattr(
            __import__("typing"), "Union", None
        ):
>           return union_type[a, b]
                   ^^^^^^^^^^^^^^^^
E           TypeError: type 'types.UnionType' is not subscriptable

site-packages/sentinel/core.py:44: TypeError
==================================== short test summary info =====================================
FAILED tests/test_contract.py::test_caller_module_is_the_defining_module - AssertionError: assert 'sentinel.core' == 'contract_subjects'
FAILED tests/test_contract.py::test_same_name_keeps_distinct_pickle_identity - AssertionError: assert MISSING is MISSING
FAILED tests/test_contract.py::test_pickle_is_a_module_lookup - AssertionError: assert b'contract_subjects' in b'\x80\x04\x95X\x00\x00\x00\x00\x00\x00\x00\x8...
FAILED tests/test_contract.py::test_custom_repr_survives_in_a_new_process - AssertionError: {'is_custom': 'False', 'repr': 'CUSTOM'}
FAILED tests/test_contract.py::test_unpickle_requires_the_defining_module - AssertionError: {'ok': 'MISSING', 'module': 'sentinel.core'}
FAILED tests/test_contract.py::test_local_sentinel_is_not_picklable - Failed: DID NOT RAISE PicklingError
FAILED tests/test_contract.py::test_module_assignment_controls_pickle - Failed: DID NOT RAISE PicklingError
FAILED tests/test_contract.py::test_union_accepts_sentinel_on_either_side - TypeError: type 'types.UnionType' is not subscriptable
8 failed in 0.11s
```
