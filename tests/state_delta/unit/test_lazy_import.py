"""
DoD #10 — lazy-hypothesis import boundary contract.

Subprocess-isolated sys.modules assertions verify that:
  1. `nwave_ai.state_delta.matcher` does NOT load hypothesis at import time.
  2. `nwave_ai.state_delta` (package root) does NOT load hypothesis at import time.

The subprocess isolation is essential: pytest itself (and its plugins) may
pre-load hypothesis in the test process.  A fresh interpreter gives a clean
sys.modules baseline.

A positive-control test also confirms hypothesis IS installed in the venv,
so the boundary tests are not false-passes due to a missing dependency.
"""

import subprocess
import sys


_ASSERTION_TEMPLATE = """
import sys
import {target}
leaked = [m for m in sys.modules if "hypothesis" in m]
assert not leaked, f"hypothesis leaked into sys.modules: {{leaked}}"
"""

_POSITIVE_CONTROL_SCRIPT = """
import hypothesis
print(hypothesis.__version__)
"""


def _run_subprocess_script(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )


def test_matcher_import_does_not_load_hypothesis() -> None:
    """Importing nwave_ai.state_delta.matcher must not pull hypothesis into sys.modules."""
    result = _run_subprocess_script(
        _ASSERTION_TEMPLATE.format(target="nwave_ai.state_delta.matcher")
    )
    assert result.returncode == 0, (
        f"hypothesis leaked after importing matcher.\nstderr: {result.stderr}"
    )
    assert result.stderr == "", f"Unexpected stderr: {result.stderr}"


def test_package_root_import_does_not_load_hypothesis() -> None:
    """Importing nwave_ai.state_delta (package root) must not pull hypothesis into sys.modules."""
    result = _run_subprocess_script(
        _ASSERTION_TEMPLATE.format(target="nwave_ai.state_delta")
    )
    assert result.returncode == 0, (
        f"hypothesis leaked after importing package root.\nstderr: {result.stderr}"
    )
    assert result.stderr == "", f"Unexpected stderr: {result.stderr}"


def test_hypothesis_is_installed_positive_control() -> None:
    """Sanity check: hypothesis must be importable in this environment.

    If this test fails, the lazy-import boundary tests above may silently
    pass for the wrong reason (hypothesis not installed rather than properly
    isolated).
    """
    result = _run_subprocess_script(_POSITIVE_CONTROL_SCRIPT)
    assert result.returncode == 0, (
        f"hypothesis is NOT installed — boundary tests may be false-passes.\n"
        f"stderr: {result.stderr}"
    )
    version = result.stdout.strip()
    assert version, "hypothesis.__version__ returned empty string"
