"""Unit tests verifying DoD #9: wheel inclusion + E2E smoke import.

Checks that:
  1. patch_pyproject.py force-include map captures nwave_ai/state_delta/**/*.py
  2. tests/e2e/test_pypi_install.py contains both smoke import assertions
     (Dockerfiles are retired per step 01-04; smoke imports live in the
      testcontainers test suite — see tests/meta/test_dockerfile_retirement.py)

These are configuration-correctness tests: they inspect artifact files
rather than executing them, so they run without Docker or a built wheel.

Step-Id: 02-06
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_PATCH_SCRIPT = _REPO_ROOT / "scripts" / "release" / "patch_pyproject.py"
_PYPI_INSTALL_TEST = _REPO_ROOT / "tests" / "e2e" / "test_pypi_install.py"


class TestStateDeltaForceInclude:
    """patch_pyproject.py must NOT include state_delta in force-include map.

    state_delta ships via packages = ["nwave_ai"] standard walk. Adding a
    force-include for the same subpath causes Hatchling to emit duplicate
    ZIP entries, which PyPI rejects (https://docs.pypi.org/archives/).
    Reverted in commit fixing v3.15.0rc1 PyPI 400 rejection.
    """

    def test_force_include_map_does_not_duplicate_state_delta(self) -> None:
        """The force-include block must NOT reference nwave_ai/state_delta."""
        script = _PATCH_SCRIPT.read_text(encoding="utf-8")
        assert '"nwave_ai/state_delta" = "nwave_ai/state_delta"' not in script, (
            "scripts/release/patch_pyproject.py MUST NOT force-include "
            "'nwave_ai/state_delta' — packages=['nwave_ai'] already ships it. "
            "Force-include creates a duplicate ZIP entry that PyPI rejects."
        )


class TestPypiInstallSmokesStateDelta:
    """test_pypi_install.py must assert state_delta importability.

    Dockerfiles are retired (step 01-04 / Phase 5 migration).
    Smoke imports live in the testcontainers-based test suite instead.
    """

    def test_smoke_assert_state_delta_present(self) -> None:
        """test_pypi_install.py must smoke-import assert_state_delta."""
        test_source = _PYPI_INSTALL_TEST.read_text(encoding="utf-8")
        assert "from nwave_ai.state_delta import assert_state_delta" in test_source, (
            "tests/e2e/test_pypi_install.py must contain a smoke-import assertion "
            "for 'assert_state_delta' from 'nwave_ai.state_delta'. "
            "Add it as a test method in TestPyPIInstall."
        )

    def test_smoke_path_strategy_present(self) -> None:
        """test_pypi_install.py must smoke-import path_strategy."""
        test_source = _PYPI_INSTALL_TEST.read_text(encoding="utf-8")
        assert (
            "from nwave_ai.state_delta.strategies import path_strategy" in test_source
        ), (
            "tests/e2e/test_pypi_install.py must contain a smoke-import assertion "
            "for 'path_strategy' from 'nwave_ai.state_delta.strategies'. "
            "This verifies the strategies subpackage ships in the wheel and "
            "that the lazy-hypothesis boundary is preserved (import does not "
            "require hypothesis at install time)."
        )
