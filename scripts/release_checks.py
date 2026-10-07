"""Version synchronization and isolated distribution checks for Gearu."""

from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "compat-sentinel"


def _version_assignment(source: str) -> ast.Assign:
    assignments = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
    ]
    if len(assignments) != 1:
        raise ValueError("expected one top-level __version__ assignment")
    assignment = assignments[0]
    if (
        len(assignment.targets) != 1
        or not isinstance(assignment.value, ast.Constant)
        or not isinstance(assignment.value.value, str)
        or assignment.lineno != assignment.end_lineno
    ):
        raise ValueError("__version__ must be a standalone string assignment")
    line = source.splitlines()[assignment.lineno - 1]
    if line[:assignment.col_offset].strip() or line[assignment.end_col_offset:].strip():
        raise ValueError("__version__ must be a standalone string assignment")
    return assignment


def _project(root: Path) -> dict:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))


def _verify_manifest(root: Path, version: str) -> None:
    project = _project(root)["project"]
    if project["name"] != PACKAGE or project["version"] != version:
        raise ValueError(f"pyproject.toml must declare {PACKAGE} {version}")


def sync_version(root: Path, version: str) -> None:
    _verify_manifest(root, version)
    path = root / "src" / "compat_sentinel" / "__init__.py"
    source = path.read_text(encoding="utf-8")
    assignment = _version_assignment(source)
    if assignment.value.value == version:
        return
    lines = source.splitlines(keepends=True)
    lines[assignment.lineno - 1] = f"__version__ = {version!r}\n"
    path.write_text("".join(lines), encoding="utf-8")


def verify_version(root: Path, version: str) -> None:
    _verify_manifest(root, version)
    source = (root / "src" / "compat_sentinel" / "__init__.py").read_text(encoding="utf-8")
    if _version_assignment(source).value.value != version:
        raise ValueError(f"compat_sentinel.__version__ must be {version}")
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = [package for package in lock["package"] if package["name"] == PACKAGE]
    if len(packages) != 1 or packages[0]["version"] != version:
        raise ValueError(f"uv.lock must record {PACKAGE} {version}")


def check_test_matrix(root: Path, version: str) -> None:
    verify_version(root, version)
    versions = _project(root)["tool"]["compat-sentinel"]["test-matrix"]["python"]
    for python in versions:
        subprocess.run(
            [
                "uv", "run", "--no-project", "--python", str(python),
                "--with", "pytest", "pytest", "-q",
            ],
            cwd=root,
            check=True,
        )


def check_distributions(root: Path, version: str) -> None:
    verify_version(root, version)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="compat-sentinel-release-check-") as directory:
        temporary = Path(directory)
        dist = temporary / "dist"
        subprocess.run(
            [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(dist)],
            cwd=root,
            env=env,
            check=True,
        )
        wheels = list(dist.glob("*.whl"))
        sdists = list(dist.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise ValueError("expected exactly one wheel and one source distribution")
        subprocess.run(
            [sys.executable, "-m", "twine", "check", str(wheels[0]), str(sdists[0])],
            cwd=temporary,
            env=env,
            check=True,
        )
        environment = temporary / "venv"
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(environment)],
            cwd=temporary,
            env=env,
            check=True,
        )
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), str(wheels[0])],
            cwd=temporary,
            env=env,
            check=True,
        )
        subprocess.run(
            [
                str(python), "-I", "-c",
                "import copy, sys; from importlib.metadata import version; "
                "import compat_sentinel; from compat_sentinel import sentinel; "
                "assert compat_sentinel.__version__ == version('compat-sentinel') == sys.argv[1]; "
                "missing = sentinel('MISSING'); "
                "assert repr(missing) == 'MISSING'; "
                "assert copy.copy(missing) is missing",
                version,
            ],
            cwd=temporary,
            env=env,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("sync-version", "verify-version", "test-matrix", "distributions"),
    )
    parser.add_argument("version")
    args = parser.parse_args()
    if args.command == "sync-version":
        sync_version(ROOT, args.version)
    elif args.command == "verify-version":
        verify_version(ROOT, args.version)
    elif args.command == "test-matrix":
        check_test_matrix(ROOT, args.version)
    else:
        check_distributions(ROOT, args.version)


if __name__ == "__main__":
    main()
