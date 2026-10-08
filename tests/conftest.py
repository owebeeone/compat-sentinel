from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--sentinel",
        choices=("compat", "pybp", "pypb"),
        default=None,
        help="sentinel implementation to load: compat (compat_sentinel) or pybp (pythonbackport-sentinel)",
    )


def pytest_configure(config: pytest.Config) -> None:
    choice = config.getoption("--sentinel") or os.environ.get("SENTINEL_IMPL", "compat")
    if choice == "pypb":
        choice = "pybp"
    if choice not in {"compat", "pybp"}:
        raise pytest.UsageError("SENTINEL_IMPL must be compat or pybp")
    config._sentinel_impl = choice  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def sentinel_impl(request: pytest.FixtureRequest) -> str:
    return request.config._sentinel_impl  # type: ignore[attr-defined]
