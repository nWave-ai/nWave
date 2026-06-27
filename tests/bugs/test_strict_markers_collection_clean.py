"""Regression guard for the pytest 9.1.x strict-markers collection regression.

pytest 9.1.0 fixed changelog #14442 — ``--strict-markers`` / ``--strict-config``
declared via ``addopts`` were silently ignored through the entire 9.0.x window.
This repo declares both (``pyproject.toml`` ``addopts``) but registers only a
small marker set, while the suite carries 142 pytest-bdd gherkin traceability
tags (``@US-3``, ``@real-io``, ``@contract-shape:bounded-change`` …). Once 9.1.x
re-enabled the gate, those unregistered tags surfaced as collection errors of
the shape::

    Failed: '<tag>' not found in `markers` configuration option

The fix promotes the existing per-track ``pytest_bdd_apply_tag`` pattern
(``tests/installer/acceptance/installer_orphan_sweep/conftest.py``) to the root
conftest, consuming gherkin metadata tags while leaving ``--strict-markers``
genuinely enforced for real ``@pytest.mark.<typo>`` mistakes.

This guard collects (no execution) representative previously-failing tracks and
asserts a clean collection. It is EXPECTED TO FAIL until the root
``pytest_bdd_apply_tag`` hook is in place.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Repo root resolution
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.parent

# Representative tracks that lacked a local pytest_bdd_apply_tag hook and so
# failed collection under genuinely-enforced --strict-markers.
_PREVIOUSLY_FAILING_DIRS = [
    "tests/feature_delta/acceptance/",
    "tests/des/acceptance/activation_gating/",
]

_MARKER_ERROR_SUBSTRING = "not found in `markers` configuration option"


@pytest.mark.fast_gate
def test_strict_markers_collection_is_clean() -> None:
    """Previously-failing tracks collect cleanly under --strict-markers."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            *_PREVIOUSLY_FAILING_DIRS,
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )

    combined_output = result.stdout + result.stderr

    assert _MARKER_ERROR_SUBSTRING not in combined_output, (
        "Unregistered pytest-bdd gherkin tag surfaced as a strict-markers "
        "collection error — the root pytest_bdd_apply_tag hook is missing or "
        f"not consuming metadata tags.\n{combined_output}"
    )
    assert result.returncode == 0, (
        f"Collection of previously-failing tracks exited {result.returncode}, "
        f"expected 0.\n{combined_output}"
    )
