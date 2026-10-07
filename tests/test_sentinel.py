from __future__ import annotations

import copy
import os
from pathlib import Path
import pickle
import subprocess
import sys
import typing
import weakref

import pytest

from compat_sentinel import sentinel
import sentinel_subjects


ROOT = Path(__file__).resolve().parents[1]


def test_each_call_returns_a_new_object() -> None:
    left = sentinel("MISSING")
    right = sentinel("MISSING")

    assert left is not right
    assert left == left
    assert left != right
    assert (left == "MISSING") is False


def test_repr_name_and_custom_repr() -> None:
    value = sentinel("MISSING")
    custom = sentinel("MISSING", repr="<missing>")

    assert repr(value) == "MISSING"
    assert str(value) == "MISSING"
    assert repr(custom) == "<missing>"
    assert str(custom) == "<missing>"
    assert value.__name__ == "MISSING"
    assert custom.__name__ == "MISSING"


def test_constructor_rejects_bad_arguments() -> None:
    with pytest.raises(TypeError):
        sentinel("MISSING", "<missing>")
    with pytest.raises(TypeError):
        sentinel(name="MISSING")
    with pytest.raises(TypeError):
        sentinel(1)
    with pytest.raises(TypeError):
        sentinel("MISSING", repr=1)


def test_caller_module_is_recorded() -> None:
    value = sentinel("LOCAL")

    assert value.__module__ == __name__


def test_attributes_are_closed() -> None:
    value = sentinel("MISSING")

    with pytest.raises(AttributeError):
        value.__name__ = "OTHER"
    with pytest.raises(AttributeError):
        value.extra = 1
    with pytest.raises(AttributeError):
        del value.__name__

    value.__module__ = "other.module"
    assert value.__module__ == "other.module"
    with pytest.raises(TypeError):
        value.__module__ = 1


def test_sentinel_is_truthy_and_hashable() -> None:
    value = sentinel("MISSING")

    assert bool(value) is True
    assert {value: "present"}[value] == "present"


def test_copy_preserves_identity() -> None:
    value = sentinel("MISSING")

    assert copy.copy(value) is value
    assert copy.deepcopy(value) is value


def test_ordering_and_weakrefs_are_rejected() -> None:
    left = sentinel("LEFT")
    right = sentinel("RIGHT")

    with pytest.raises(TypeError):
        left < right
    with pytest.raises(TypeError):
        weakref.ref(left)


def test_subclassing_is_rejected() -> None:
    with pytest.raises(TypeError):

        class Child(sentinel):
            pass


def test_union_accepts_sentinel_on_either_side() -> None:
    value = sentinel("MISSING")
    forward = int | value
    reverse = value | str

    assert forward == typing.Union[int, value]
    assert reverse == typing.Union[value, str]
    assert value in typing.get_args(forward)
    assert value in typing.get_args(reverse)


def test_module_global_pickle_preserves_identity() -> None:
    restored = pickle.loads(pickle.dumps(sentinel_subjects.MISSING))

    assert restored is sentinel_subjects.MISSING


def test_custom_repr_survives_pickle() -> None:
    restored = pickle.loads(pickle.dumps(sentinel_subjects.CUSTOM))

    assert restored is sentinel_subjects.CUSTOM
    assert repr(restored) == "<custom>"


def test_pickle_uses_module_and_name_lookup() -> None:
    blob = pickle.dumps(sentinel_subjects.MISSING)

    assert b"sentinel_subjects" in blob
    assert b"MISSING" in blob
    assert b"_reconstruct" not in blob


def test_same_name_does_not_share_pickle_identity() -> None:
    assert sentinel_subjects.SAME_NAME is not sentinel_subjects.MISSING
    with pytest.raises(pickle.PicklingError):
        pickle.dumps(sentinel_subjects.SAME_NAME)


def test_class_attribute_pickle_preserves_identity() -> None:
    restored = pickle.loads(pickle.dumps(sentinel_subjects.Box.SHORT))

    assert restored is sentinel_subjects.Box.SHORT
    assert repr(restored) == "Box.SHORT"


def test_unassigned_sentinel_is_not_picklable() -> None:
    value = sentinel("EPHEMERAL")

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(value)


def test_writable_module_controls_pickle_lookup() -> None:
    holder = sentinel("HOLDER")
    globals()["HOLDER"] = holder
    try:
        assert pickle.loads(pickle.dumps(holder)) is holder
        holder.__module__ = "not.a.real.module"
        with pytest.raises(pickle.PicklingError):
            pickle.dumps(holder)
    finally:
        del globals()["HOLDER"]


def test_other_process_resolves_the_defining_module() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT / "tests"), env.get("PYTHONPATH", "")]
    )
    env.pop("PYTHONSAFEPATH", None)
    script = """
import pickle
import sys

blob = sys.stdin.buffer.read()
restored = pickle.loads(blob)
import sentinel_subjects
print("missing", restored is sentinel_subjects.MISSING)
print("repr", repr(restored))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=pickle.dumps(sentinel_subjects.CUSTOM),
        capture_output=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr.decode()
    assert completed.stdout.decode().splitlines() == [
        "missing False",
        "repr <custom>",
    ]

    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=pickle.dumps(sentinel_subjects.MISSING),
        capture_output=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr.decode()
    assert completed.stdout.decode().splitlines() == [
        "missing True",
        "repr MISSING",
    ]
