"""PEP 661 ``sentinel`` for interpreters that do not provide the builtin."""

from __future__ import annotations

import sys
from typing import Union


class sentinel:
    """Unique sentinel object.

    ``sentinel(name, /, *, repr=None)`` matches the Python 3.15 builtin.
    Each call returns a new object. Pickle preserves identity only when the
    sentinel can be imported from its ``__module__`` under ``__name__``.
    """

    __slots__ = ("_name", "_module", "_repr")

    def __init_subclass__(cls) -> None:
        raise TypeError("subclassing sentinel is not supported")

    def __new__(cls, name: str, /, *, repr: str | None = None) -> sentinel:
        if cls is not sentinel:
            raise TypeError("sentinel() may not be invoked from a subclass")
        if not isinstance(name, str):
            raise TypeError(f"sentinel name must be a str, not {type(name).__name__}")
        if repr is not None and not isinstance(repr, str):
            raise TypeError(f"sentinel repr must be a str, not {type(repr).__name__}")

        instance = object.__new__(cls)
        object.__setattr__(instance, "_name", name)
        object.__setattr__(instance, "_module", _caller_module())
        object.__setattr__(instance, "_repr", name if repr is None else repr)
        return instance

    def __getattribute__(self, name: str) -> object:
        if name == "__name__":
            return object.__getattribute__(self, "_name")
        if name == "__module__":
            return object.__getattribute__(self, "_module")
        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "__module__":
            if not isinstance(value, str):
                raise TypeError(f"__module__ must be a str, not {type(value).__name__}")
            object.__setattr__(self, "_module", value)
            return
        if name == "__name__":
            raise AttributeError("readonly attribute")
        raise AttributeError(f"'sentinel' object has no attribute {name!r}")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"'sentinel' object has no attribute {name!r}")

    def __repr__(self) -> str:
        return object.__getattribute__(self, "_repr")

    def __str__(self) -> str:
        return object.__getattribute__(self, "_repr")

    def __bool__(self) -> bool:
        return True

    def __hash__(self) -> int:
        return object.__hash__(self)

    def __eq__(self, other: object) -> bool:
        return self is other

    def __copy__(self) -> sentinel:
        return self

    def __deepcopy__(self, memo: object) -> sentinel:
        return self

    def __reduce__(self) -> str:
        return object.__getattribute__(self, "_name")

    def __or__(self, other: object) -> object:
        return Union[self, other]

    def __ror__(self, other: object) -> object:
        return Union[other, self]


def _caller_module() -> str:
    """Return the module that called ``sentinel()``.

    ``__new__`` is the direct caller, so the user frame is one level above it.
    """

    module_name = sys._getframemodulename(2)
    if module_name is None:
        module_name = sys._getframe(2).f_globals.get("__name__", "__main__")
    if not isinstance(module_name, str) or module_name == "":
        return "__main__"
    return module_name
