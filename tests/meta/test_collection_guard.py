"""Meta test for the top-level test-module collection guard.

The guard lives in ``tests/conftest.py`` and refuses to collect test
modules placed at the top level of ``tests/`` (i.e. ``tests/test_*.py``).
The structural rule is documented in
``docs/analysis/rca-attribution-plugin-worktree-isolation.md`` Branch B:
top-level modules historically drifted out of sync with their canonical
siblings under ``tests/installer/``, ``tests/des/``, etc.

This meta test exercises the guard by running a sub-pytest collection
against a fixture tests-tree that contains exactly one offending file.
We assert that pytest's exit code signals the failure AND that the error
message references the RCA.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.xdist_group("collection_guard_meta")


CONFTEST_UNDER_TEST = Path(__file__).resolve().parents[1] / "conftest.py"


def _build_fixture_tree(root: Path, *, with_offender: bool) -> None:
    """Create a minimal tests/ tree with the real conftest copied in.

    When ``with_offender`` is True, a top-level ``test_offender.py`` is
    placed directly under ``root``; that's the violation the guard must
    reject. When False, the tree contains only a tier-subdir test, which
    must collect cleanly.
    """
    root.mkdir(parents=True, exist_ok=True)
    # Copy the real conftest verbatim so we exercise the SAME guard.
    (root / "conftest.py").write_text(
        CONFTEST_UNDER_TEST.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # Tier-subdir test — must always be collectible.
    tier = root / "unit"
    tier.mkdir()
    (tier / "__init__.py").write_text("")
    (tier / "test_legitimate.py").write_text("def test_smoke():\n    assert True\n")
    if with_offender:
        (root / "test_offender.py").write_text(
            "def test_should_never_collect():\n    assert True\n"
        )


def _run_pytest_collect(rootdir: Path) -> subprocess.CompletedProcess[str]:
    """Run ``pytest --collect-only`` against ``rootdir``. No xdist."""
    # IMPORTANT: subprocess inherits PATH but we want a clean rootdir/ini.
    # We pass ``rootdir`` as the test directory and disable user/global
    # plugins via ``-p no:cacheprovider`` to avoid coupling.
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xdist",
            str(rootdir),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=rootdir,
    )


class TestTopLevelTestModuleGuard:
    """Contract: top-level ``tests/test_*.py`` must fail collection."""

    def test_offending_top_level_module_blocks_collection(self, tmp_path: Path) -> None:
        """A top-level ``test_*.py`` placed directly under the tests root
        must cause pytest collection to fail with a non-zero exit code
        AND a message referencing the RCA.
        """
        tests_root = tmp_path / "tests"
        _build_fixture_tree(tests_root, with_offender=True)

        result = _run_pytest_collect(tests_root)

        assert result.returncode != 0, (
            "Pytest collection MUST fail when a top-level test module is "
            f"present. stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        combined = result.stdout + result.stderr
        assert "test_offender.py" in combined, (
            f"Guard error must name the offending file. Got: {combined!r}"
        )
        assert "rca-attribution-plugin-worktree-isolation" in combined, (
            "Guard error must reference the RCA so future devs find context. "
            f"Got: {combined!r}"
        )

    def test_clean_tier_subdir_tests_collect(self, tmp_path: Path) -> None:
        """A tree without any top-level test module collects cleanly,
        proving the guard does not over-reach.
        """
        tests_root = tmp_path / "tests"
        _build_fixture_tree(tests_root, with_offender=False)

        result = _run_pytest_collect(tests_root)

        assert result.returncode == 0, (
            "Clean tree must collect successfully; guard must not over-fire. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "test_legitimate" in result.stdout, (
            f"Tier-subdir test must be collected. Got: {result.stdout!r}"
        )
