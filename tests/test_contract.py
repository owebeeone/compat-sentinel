"""PEP 661 contract checks for the selected sentinel implementation.

    uv run --with pytest pytest -q
    uv run --python 3.13 --with pytest --with pythonbackport-sentinel pytest -q --sentinel=pybp tests/test_contract.py

``--sentinel=compat`` (the default) loads ``compat_sentinel.sentinel``.
``--sentinel=pybp`` loads ``sentinel.sentinel`` from pythonbackport-sentinel.
``SENTINEL_IMPL`` selects the same way when the option is omitted.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import pickle
import subprocess
import sys
import textwrap
import typing

import pytest


@pytest.fixture(scope="module")
def sentinel(sentinel_impl: str):
    if sentinel_impl == "compat":
        from compat_sentinel import sentinel as loaded
    else:
        try:
            from sentinel import sentinel as loaded
        except ImportError as exc:
            pytest.fail(f"pythonbackport-sentinel is not installed ({exc})")
    return loaded


@pytest.fixture(scope="module")
def subjects(sentinel_impl: str, sentinel, tmp_path_factory: pytest.TempPathFactory):
    directory = tmp_path_factory.mktemp("contract-subjects")
    module_name = "contract_subjects"
    import_line = (
        "from compat_sentinel import sentinel"
        if sentinel_impl == "compat"
        else "from sentinel import sentinel"
    )
    (directory / f"{module_name}.py").write_text(
        textwrap.dedent(
            f"""\
            {import_line}

            MISSING = sentinel("MISSING")
            SAME_NAME = sentinel("MISSING")
            CUSTOM = sentinel("CUSTOM", repr="<custom>")
            HOLDER = sentinel("HOLDER")
            """
        ),
        encoding="utf-8",
    )
    sys.path.insert(0, str(directory))
    sys.modules.pop(module_name, None)
    try:
        module = importlib.import_module(module_name)
        module.SUBJECTS_DIR = directory
        yield module
    finally:
        sys.path.remove(str(directory))
        sys.modules.pop(module_name, None)


def test_caller_module_is_the_defining_module(subjects) -> None:
    assert subjects.MISSING.__module__ == subjects.__name__


def test_same_name_keeps_distinct_pickle_identity(subjects) -> None:
    restored = pickle.loads(pickle.dumps(subjects.MISSING))

    assert restored is subjects.MISSING
    assert restored is not subjects.SAME_NAME


def test_pickle_is_a_module_lookup(subjects) -> None:
    blob = pickle.dumps(subjects.MISSING)

    assert subjects.__name__.encode() in blob
    assert b"_reconstruct" not in blob


def test_custom_repr_survives_in_a_new_process(subjects) -> None:
    report = _child("with-module", pickle.dumps(subjects.CUSTOM), subjects)

    assert report.get("is_custom") == "True", report
    assert report.get("repr") == "<custom>", report


def test_unpickle_requires_the_defining_module(subjects) -> None:
    report = _child("no-module", pickle.dumps(subjects.MISSING), subjects)

    assert report.get("error") == "ModuleNotFoundError", report


def test_local_sentinel_is_not_picklable(sentinel) -> None:
    value = sentinel("EPHEMERAL")

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(value)


def test_module_assignment_controls_pickle(subjects) -> None:
    original = subjects.HOLDER.__module__
    subjects.HOLDER.__module__ = "not.a.real.module"
    try:
        with pytest.raises(pickle.PicklingError):
            pickle.dumps(subjects.HOLDER)
    finally:
        subjects.HOLDER.__module__ = original


def test_union_accepts_sentinel_on_either_side(sentinel) -> None:
    value = sentinel("UNION")
    forward = int | value
    reverse = value | str

    assert value in typing.get_args(forward)
    assert value in typing.get_args(reverse)


def _child(mode: str, blob: bytes, subjects) -> dict[str, str]:
    directory = Path(subjects.SUBJECTS_DIR)
    env = os.environ.copy()
    entries = [str(directory)]
    entries.extend(entry for entry in sys.path if entry and entry not in entries)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    env.pop("PYTHONSAFEPATH", None)
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, mode, subjects.__name__, str(directory)],
        input=blob,
        capture_output=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode().strip().splitlines()
        return {"error": detail[-1] if detail else f"exit {completed.returncode}"}
    report: dict[str, str] = {}
    for line in completed.stdout.decode().splitlines():
        key, _, value = line.partition(" ")
        report[key] = value
    return report


_CHILD = r"""
import pickle
import sys

mode, module_name, directory = sys.argv[1:]
blob = sys.stdin.buffer.read()
if mode == "no-module":
    sys.path = [entry for entry in sys.path if entry != directory]
try:
    obj = pickle.loads(blob)
except Exception as exc:
    print("error", type(exc).__name__)
else:
    if mode == "with-module":
        module = __import__(module_name)
        print("is_custom", obj is module.CUSTOM)
        print("repr", repr(obj))
    else:
        print("ok", repr(obj))
        print("module", obj.__module__)
"""
