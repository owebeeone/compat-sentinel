"""compat_sentinel — PEP 661 sentinel for Python 3.12 and later."""

__version__ = "0.1.0"

try:
    from builtins import sentinel as sentinel
except ImportError:
    from compat_sentinel._sentinel import sentinel

    sentinel.__module__ = __name__

__all__ = [
    "__version__",
    "sentinel",
]
