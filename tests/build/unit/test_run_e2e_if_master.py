"""Tests for the unconditional e2e pre-push wrapper.

Per Ale 2026-05-19 mandate: e2e runs on EVERY push regardless of
branch. Previous version (branch-conditional) had a bypass bug where
`git push origin feature:master` skipped e2e because the LOCAL branch
name was checked instead of the destination ref. The fix removes all
conditional logic — e2e is unconditional on pre-push.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


WRAPPER_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "hooks" / "run_e2e_if_master.py"
)


def _load_wrapper_module():
    """Load the wrapper script as a module, fail clearly if absent."""
    assert WRAPPER_PATH.is_file(), f"wrapper script missing at {WRAPPER_PATH}"
    spec = importlib.util.spec_from_file_location(
        "run_e2e_if_master_under_test", WRAPPER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wrapper():
    """Load the wrapper module fresh for each test (clean monkeypatched state)."""
    return _load_wrapper_module()


def test_unconditional_invokes_pytest_on_any_push(wrapper) -> None:
    """The wrapper invokes pytest unconditionally on every push.

    Branch name is irrelevant — pre-push hook runs e2e always.
    """
    with patch.object(wrapper.subprocess, "run") as mock_run:
        mock_run.return_value.returncode = 0
        exit_code = wrapper.main([])

    assert exit_code == 0
    assert mock_run.call_count == 1, "pytest must be invoked on every push"
    cmd = mock_run.call_args.args[0]
    # Pre-push runs only the smoke subset (4 critical-path files);
    # full e2e remains on CI per PR.
    assert "uv" in cmd[0] or "pytest" in " ".join(cmd), (
        f"Expected pytest invocation, got: {cmd}"
    )
    assert "-m" in cmd, f"Expected ``-m`` selector, got: {cmd}"
    marker_expr = cmd[cmd.index("-m") + 1]
    assert "e2e" in marker_expr and "e2e_smoke" in marker_expr, (
        f"Expected ``e2e and e2e_smoke`` marker expression, got: {marker_expr!r}"
    )


def test_pytest_failure_propagates_nonzero_exit(wrapper) -> None:
    """If pytest returns non-zero, the wrapper exits non-zero.

    A failed e2e suite must block the push — that's the whole point
    of the gate.
    """
    with patch.object(wrapper.subprocess, "run") as mock_run:
        mock_run.return_value.returncode = 1
        exit_code = wrapper.main([])

    assert exit_code != 0, "pytest failure must propagate as non-zero exit code"


def test_passes_through_argv_to_pytest(wrapper) -> None:
    """Additional argv passes through to pytest invocation.

    Allows callers to inject extra pytest flags (e.g. --tb=long).
    """
    with patch.object(wrapper.subprocess, "run") as mock_run:
        mock_run.return_value.returncode = 0
        wrapper.main(["--tb=long", "-x"])

    cmd = mock_run.call_args.args[0]
    assert "--tb=long" in cmd, "extra argv must pass through to pytest"
    assert "-x" in cmd, "extra argv must pass through to pytest"
