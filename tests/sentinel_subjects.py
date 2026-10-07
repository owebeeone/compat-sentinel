"""Importable sentinels used to check pickle identity."""

from compat_sentinel import sentinel


MISSING = sentinel("MISSING")
CUSTOM = sentinel("CUSTOM", repr="<custom>")
SAME_NAME = sentinel("MISSING")


class Box:
    SHORT = sentinel("Box.SHORT")
