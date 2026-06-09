"""Pytest wrapper for the Windows native smoke test.

Wraps ``tests/e2e/smoke_test_windows.py`` as a pytest-discoverable test so
it runs in the standard CI test suite with proper markers and skip behaviour.

The underlying script is a standalone module with its own PASS/FAIL tracking.
It is NOT imported here — it is invoked as a subprocess to preserve its
``sys.exit()`` semantics and avoid side-effects from module-level code that
runs on import (print statements, tempdir setup, etc.).

This test is skipped on non-Windows platforms.  In CI it runs on the
``windows-latest`` runner (the native execution environment for Windows
validation) and is not expected to run on Linux/macOS.

Step-Id: 01-01
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).parent.parent.parent
_SMOKE_SCRIPT = _REPO_ROOT / "tests" / "e2e" / "smoke_test_windows.py"


@pytest.mark.e2e
@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows smoke test — only runs on Windows (skip on Linux/macOS)",
)
class TestWindowsSmoke:
    """Runs the Windows native smoke test as a subprocess and checks exit code.

    Skipped on non-Windows platforms.  In CI this class runs on the
    ``windows-latest`` GitHub Actions runner.

    The smoke script validates:
    - pip install nwave-ai into a temporary venv
    - nwave-ai version reports a version string
    - nwave-ai install deploys agents and skills
    - git commit succeeds in a temporary repo
    """

    def test_windows_smoke_script_exits_zero(self) -> None:
        """smoke_test_windows.py must exit 0 (all sub-tests pass).

        The script uses its own PASS/FAIL counter and exits with the failure
        count.  Exit 0 means every sub-test passed.
        """
        result = subprocess.run(
            [sys.executable, str(_SMOKE_SCRIPT)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        assert result.returncode == 0, (
            f"smoke_test_windows.py exited {result.returncode} (expected 0).\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
