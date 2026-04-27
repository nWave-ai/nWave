"""Wheel invariant: every UTILITY_SCRIPTS entry must be force-included.

Bug-fix regression guard for v3.12.1 install regression
(docs/analysis/rca-v3-12-1-install-regression.md, Bug #1).

The dev-build whitelist `scripts.build_dist.UTILITY_SCRIPTS` enumerates the
top-level scripts (e.g. install_nwave_target_hooks.py, validate_step_file.py)
that the installer's verifier expects under <install_root>/scripts/. Those
scripts ship correctly into the dev tarball, but they were ABSENT from the
PyPI wheel because `scripts/release/patch_pyproject.py` rewrites the
[tool.hatch.build.targets.wheel.force-include] block and historically only
declared the `scripts/install` and `scripts/shared` SUBDIRECTORIES — never the
top-level utility files. Result: PyPI wheel `nwave_ai==3.12.1` shipped with
those scripts missing, installer reported "Scripts verified (0/0)" and failed.

This module locks the invariant: every entry of `UTILITY_SCRIPTS` MUST be
referenced as a force-include source key in the patched pyproject.toml.
The test FAILS before the fix (entries omitted from the force-include map)
and PASSES after the fix (entries added).

Pure assertion over the patcher's textual output — no subprocess, no real
build invocation. The patcher's regex generator is fully deterministic, so
checking for the exact `"name" = "name"` line proves the wheel build will
include the source file at the same destination.

BDD scenario mapping:
  - fix-v3-12-2-install-regression / step 01-01:
    "PyPI wheel ships every utility script declared in build_dist".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


# ``scripts/build_dist.py`` lives at the repository root and is not part of any
# package; resolve its parent on sys.path before importing UTILITY_SCRIPTS.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_dist import UTILITY_SCRIPTS  # noqa: E402

from scripts.release.patch_pyproject import patch_pyproject  # noqa: E402


def _patched_text(sample_pyproject_path: str, tmp_path) -> str:
    """Run the patcher against the shared fixture and return the rewritten TOML."""
    output_path = str(tmp_path / "patched.toml")
    patch_pyproject(
        input_path=sample_pyproject_path,
        output_path=output_path,
        target_name="nwave-ai",
        target_version="0.0.0",
    )
    return Path(output_path).read_text()


class TestUtilityScriptsForceIncluded:
    """Every UTILITY_SCRIPTS entry is referenced in the wheel force-include map."""

    @pytest.mark.parametrize("script_name", UTILITY_SCRIPTS)
    def test_utility_script_is_force_included(
        self, script_name: str, sample_pyproject_path, tmp_path
    ):
        """For each utility script, the patched pyproject MUST contain a
        force-include entry mapping the top-level ``scripts/<name>.py`` source
        path to the same destination inside the wheel.

        Failure mode this catches: the entry is missing from
        `_patch_wheel_packages` in scripts/release/patch_pyproject.py, which
        produces a wheel without the utility script, which makes
        installation_verifier report 0 scripts and abort.
        """
        content = _patched_text(sample_pyproject_path, tmp_path)
        expected_entry = f'"scripts/{script_name}" = "scripts/{script_name}"'
        assert expected_entry in content, (
            f"Utility script '{script_name}' is not force-included in the "
            "wheel. Expected line in patched pyproject.toml's "
            "[tool.hatch.build.targets.wheel.force-include] block:\n"
            f"  {expected_entry}\n\n"
            "If you removed an entry from UTILITY_SCRIPTS, also remove it "
            "from scripts/release/patch_pyproject.py:_patch_wheel_packages. "
            "If you added an entry to UTILITY_SCRIPTS, also add the "
            "force-include declaration there."
        )


class TestForceIncludeMapInvariant:
    """The force-include block remains complete: every dev-build whitelist
    entry has a matching wheel declaration."""

    def test_no_utility_script_silently_dropped(self, sample_pyproject_path, tmp_path):
        """Equivalence between dev-tarball and PyPI-wheel utility coverage.

        Ensures the two whitelists never drift: dev tarball
        (`build_dist.UTILITY_SCRIPTS`) and PyPI wheel (force-include block)
        agree on which top-level scripts ship to users.
        """
        content = _patched_text(sample_pyproject_path, tmp_path)
        missing = [
            name
            for name in UTILITY_SCRIPTS
            if f'"scripts/{name}" = "scripts/{name}"' not in content
        ]
        assert not missing, (
            "UTILITY_SCRIPTS entries missing from wheel force-include map: "
            f"{missing}. The PyPI wheel will ship without these scripts, "
            "and installation_verifier will report 'Scripts verified (0/N)'. "
            "Fix: add a force-include line for each missing script in "
            "scripts/release/patch_pyproject.py:_patch_wheel_packages."
        )
