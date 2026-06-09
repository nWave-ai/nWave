"""E2E regression guard for the v3.12.x PyPI install chain.

Why this test exists
--------------------

The 4 v3.12.1 install-path bugs (Bugs #1-#4 enumerated below) were not
caught by any existing e2e test even though the e2e suite was green.
Four systemic gaps in the existing coverage:

1. **Wrong entry point** — every existing e2e test invokes
   ``python -m nwave_ai.cli install`` (e.g. ``test_fresh_install.py:154``,
   ``test_idempotent_install.py``, ``test_pypi_install.py:138``). Real users
   invoke the ``nwave-ai`` console-script binary registered by the wheel's
   ``[project.scripts]`` block. Console-script regressions are invisible to
   tests that import the module directly.

2. **Wrong wheel shape** — existing tests build the dev-shape wheel via
   ``python -m build --wheel`` against the source ``pyproject.toml``. They
   never apply ``scripts/release/patch_pyproject.py``, so the PyPI wheel's
   force-include map (which omitted utility scripts in v3.12.1, Bug #1) is
   never exercised.

3. **PYTHONPATH masking** — existing containers mount the source tree at
   ``/src`` and run with ``PYTHONPATH=/src``. The installer's
   ``script_files = [s for s in utility_scripts if (scripts_source / s).exists()]``
   then sees the source files even when the wheel omits them, masking the
   verifier's ``script_expected > 0`` cliff (Bug #2).

4. **Permissive doctor assertion** — the existing doctor probe
   (``test_fresh_install.py:408``) asserts ``not failed_critical``, which
   tolerates the stale ``commands/: missing`` false positive (Bug #4).

This test closes all four gaps by reproducing the *exact* end-user chain:

    scripts/build_dist.py
        |
        v
    cp -r dist/lib ./lib                  # for force-include resolution
        |
        v
    scripts/release/patch_pyproject.py    # PyPI wheel shape
        |
        v
    python -m build --wheel               # opaque distributable
        |
        v
    pip install <wheel>  (clean venv, isolated $HOME)
        |
        v
    nwave-ai install     (CONSOLE SCRIPT, not python -m)
        |
        v
    nwave-ai doctor      (CONSOLE SCRIPT)

and asserts the strict success contract:

  - install:     "Deployment validated" + 4/4 component checks pass
                 (specifically Scripts verified (2/2), locking Bug #2 fix)
  - doctor:      "8/8 checks passed" with zero failures
                 (specifically framework_files passes, locking Bug #4 fix;
                 8th check added in v3.14 — DensityCheck per D6/D12)

Implementation notes
--------------------

- A host-level ``python -m venv`` with ``HOME`` redirected to a tmp directory
  is sufficient: the bug class is wheel-shape + console-script entry point,
  not OS-level isolation. Using a venv (instead of testcontainers) keeps the
  test fast (~60s) and cuts the Docker dependency for this regression class.

- The build is session-scoped to amortize the ~30s wheel build across the
  install + doctor assertions.

- The repo is *never* mutated. A minimal subset of source dirs is copied to a
  per-session tmp directory, ``pyproject.toml`` is patched in that copy, and
  ``python -m build --wheel`` runs there. The original repo's ``lib/`` and
  ``dist/`` directories are not created; ``build_dist.py`` runs against the
  tmp copy too.

RED -> GREEN proof recorded in commit message: reverting any of the 4 v3.12.2
fix commits (585ace87, 88e2d53a, 1676aa96, 52b3369c) makes this test fail.

Step-Id: regression-guard for fix-v3-12-2-install-regression
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path


pytestmark = pytest.mark.e2e_smoke

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Note: _REPO_ROOT, _SANDBOX_INCLUDES, _copy_repo_subset, _build_pypi_shape_wheel,
# and the `pypi_shape_wheel` session fixture have been moved to tests/e2e/conftest.py
# so they can be shared with test_wheel_privacy_contract.py (closes Root Cause A
# of the wheel_privacy_container live-PyPI catch-22, fix-wheel-privacy-self-blocking-gate
# step 01-02).  The `pypi_shape_wheel` fixture is auto-injected from conftest.

# Runtime deps required by nwave_ai/cli.py and scripts/install/install_nwave.py.
# Mirrors the runtime stanza used by other e2e tests (test_pypi_install.py:117,
# test_fresh_install.py).
_RUNTIME_DEPS: tuple[str, ...] = (
    "rich",
    "typer",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "platformdirs",
    "pyyaml",
    "packaging",
    "tomli",  # Python 3.10 fallback used by patch_pyproject and others
    "build",  # for python -m build --wheel
)


# ---------------------------------------------------------------------------
# Pure helpers (port-to-port at process boundary)
# ---------------------------------------------------------------------------


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> tuple[int, str]:
    """Run a subprocess and return (exit_code, combined_stdout_stderr).

    Pure helper: no implicit cwd, no implicit env. Caller passes everything
    explicitly so the test reads as a deterministic pipeline.
    """
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


def _wheel_contains(wheel: Path, *paths: str) -> dict[str, bool]:
    """Return {path: present} for each *path* against the wheel's contents."""
    import zipfile

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
    # Wheel paths use forward slashes regardless of OS.
    return {p: p in names for p in paths}


# ---------------------------------------------------------------------------
# Session-scoped fixtures (amortize the ~60s build)
# ---------------------------------------------------------------------------
# `pypi_shape_wheel` is provided by tests/e2e/conftest.py — auto-injected as a
# fixture parameter below.


@pytest.fixture(scope="session")
def installed_console_script(
    pypi_shape_wheel: Path, tmp_path_factory
) -> tuple[Path, Path, str]:
    """Install the wheel into a clean venv with isolated HOME and run install.

    Returns (venv_path, fake_home, install_stdout). The console script is at
    venv_path / "bin" / "nwave-ai". The fake_home is the simulated user
    home where ~/.claude/ has been deployed by `nwave-ai install`.

    This fixture exercises the FULL end-user chain in isolation:
      pip install <wheel> -> nwave-ai install -> capture stdout

    The doctor invocation lives in a separate test method to keep assertions
    granular.
    """
    venv = tmp_path_factory.mktemp("nwave_pypi_venv") / "venv"
    fake_home = tmp_path_factory.mktemp("nwave_fake_home")

    # 1. Create venv
    code, out = _run([sys.executable, "-m", "venv", str(venv)])
    assert code == 0, f"venv creation failed (exit {code}):\n{out}"

    venv_python = venv / "bin" / "python"
    venv_pip = venv / "bin" / "pip"
    assert venv_python.is_file(), f"venv python missing: {venv_python}"

    # 2. Install runtime deps + the wheel itself.
    # `pip install <wheel>` will pull deps from pyproject's [project] block;
    # we pre-install the runtime deps explicitly to keep the test offline-friendly
    # for the deps that are guaranteed-installed already and to fail fast on
    # missing PyPI-listed deps.
    code, out = _run(
        [str(venv_pip), "install", "--quiet", *_RUNTIME_DEPS],
        timeout=300,
    )
    assert code == 0, f"runtime deps install failed (exit {code}):\n{out}"

    code, out = _run(
        [str(venv_pip), "install", "--quiet", str(pypi_shape_wheel)],
        timeout=300,
    )
    assert code == 0, f"wheel install failed (exit {code}):\n{out}"

    # 3. Pre-create minimal ~/.claude/settings.json (installer preflight needs it).
    claude_dir = fake_home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(
        '{"permissions": {}, "hooks": {}}', encoding="utf-8"
    )

    # 4. Run `nwave-ai install` via CONSOLE SCRIPT (not `python -m`).
    console_script = venv / "bin" / "nwave-ai"
    assert console_script.is_file(), (
        f"nwave-ai console script missing in venv at {console_script}. "
        "[project.scripts] entry was not registered by the wheel."
    )

    # Strict environment: HOME redirected, NO PYTHONPATH (would mask Bug #2).
    install_env = {
        "HOME": str(fake_home),
        "PATH": f"{venv / 'bin'}:{os.environ.get('PATH', '')}",
        # Auto-confirm any interactive prompts (matches `echo y |` pattern in
        # test_pypi_install.py:138).
        "NWAVE_AUTO_CONFIRM": "1",
    }
    # Pipe "y\n" repeatedly via stdin to be safe with prompt() calls.
    proc = subprocess.run(
        [str(console_script), "install"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input=b"y\n" * 20,
        env=install_env,
        timeout=600,
        check=False,
    )
    install_stdout = proc.stdout.decode("utf-8", errors="replace")
    assert proc.returncode == 0, (
        f"`nwave-ai install` failed (exit {proc.returncode}).\n"
        f"--- stdout ---\n{install_stdout}"
    )

    return venv, fake_home, install_stdout


# ---------------------------------------------------------------------------
# Tests — all share the session-built wheel + venv
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestPyPIShapeWheelContents:
    """Locks Bug #1: wheel must contain utility scripts + framework assets."""

    def test_wheel_contains_console_script_module(self, pypi_shape_wheel: Path) -> None:
        """The CLI module that backs the `nwave-ai` console script."""
        present = _wheel_contains(pypi_shape_wheel, "nwave_ai/cli.py")
        assert present["nwave_ai/cli.py"], (
            "nwave_ai/cli.py missing from PyPI wheel — console script entry "
            "point would have nothing to call.\n"
            f"Wheel: {pypi_shape_wheel}"
        )

    def test_wheel_contains_utility_scripts(self, pypi_shape_wheel: Path) -> None:
        """Bug #1: scripts/install_nwave_target_hooks.py and validate_step_file.py
        MUST be in the wheel. Their absence in v3.12.1 made the verifier report
        "Scripts verified (0/0)" and fail validation.
        """
        targets = (
            "scripts/install_nwave_target_hooks.py",
            "scripts/validate_step_file.py",
        )
        present = _wheel_contains(pypi_shape_wheel, *targets)
        missing = [p for p, ok in present.items() if not ok]
        assert not missing, (
            f"PyPI wheel missing utility scripts: {missing}.\n"
            "This is the v3.12.1 Bug #1 regression — patch_pyproject.py "
            "force-include map dropped these top-level scripts.\n"
            f"Wheel: {pypi_shape_wheel}"
        )

    def test_wheel_contains_installer_orchestrator(
        self, pypi_shape_wheel: Path
    ) -> None:
        """The installer entry point must be in the wheel."""
        present = _wheel_contains(pypi_shape_wheel, "scripts/install/install_nwave.py")
        assert present["scripts/install/install_nwave.py"], (
            "scripts/install/install_nwave.py missing from wheel.\n"
            f"Wheel: {pypi_shape_wheel}"
        )

    def test_wheel_contains_framework_assets(self, pypi_shape_wheel: Path) -> None:
        """At least one agent + one task file from nWave/ must ship."""
        import zipfile

        with zipfile.ZipFile(pypi_shape_wheel) as zf:
            names = zf.namelist()
        agent_files = [n for n in names if n.startswith("nWave/agents/nw-")]
        task_files = [n for n in names if n.startswith("nWave/tasks/nw/")]
        assert agent_files, f"No nWave/agents/nw-* files in wheel: {pypi_shape_wheel}"
        assert task_files, f"No nWave/tasks/nw/* files in wheel: {pypi_shape_wheel}"


@pytest.mark.e2e
class TestPyPIShapeInstallChain:
    """Locks Bug #2 + Bug #3: console-script install + Scripts verified (2/2)."""

    def test_install_reports_deployment_validated(
        self, installed_console_script
    ) -> None:
        """The installer MUST end with `Deployment validated` and exit 0.

        Asserted indirectly by the fixture (which raises on non-zero exit) and
        directly here against the captured stdout.
        """
        _, _, stdout = installed_console_script
        assert "Deployment validated" in stdout, (
            "Install completed but did not emit 'Deployment validated'. "
            "Either validation silently failed or the success path was not "
            "reached.\n--- stdout ---\n" + stdout
        )
        # Negative checks: failure markers must NOT appear
        for forbidden in (
            "Validation failed",
            "Installation failed validation",
            "sync mismatch",
        ):
            assert forbidden not in stdout, (
                f"Install stdout contains forbidden marker {forbidden!r}.\n"
                f"--- stdout ---\n{stdout}"
            )

    def test_all_four_components_pass(self, installed_console_script) -> None:
        """All 4 component verifiers (agents/commands/templates/scripts) MUST be ✅.

        Locks Bug #2: `Scripts verified (2/2)` (not 0/0). Locks Bug #3: every
        component reports its own status (no opaque "agent/command sync mismatch").
        """
        _, _, stdout = installed_console_script
        for component in (
            "Agents verified",
            "Commands verified",
            "Templates verified",
            "Scripts verified",
        ):
            # Find the component line and verify it is prefixed with ✅
            matching = [line for line in stdout.splitlines() if component in line]
            assert matching, (
                f"{component!r} not found in install stdout.\n--- stdout ---\n{stdout}"
            )
            for line in matching:
                assert "✅" in line, (
                    f"{component!r} did not pass: {line.strip()!r}\n"
                    f"--- stdout ---\n{stdout}"
                )
                assert "❌" not in line, (
                    f"{component!r} reported failure: {line.strip()!r}"
                )

    def test_scripts_verified_two_of_two(self, installed_console_script) -> None:
        """Specifically: Scripts MUST be (2/2). Locks Bug #2 fix.

        With v3.12.1 force-include omission + script_expected > 0 cliff:
        - utility_scripts present in source = 0 (wheel didn't ship them)
        - script_expected = 0
        - script_ok = (0 == 0) and (0 > 0)  ==>  False
        - All synced = False -> install fails.

        Post-fix:
        - utility_scripts present = 2
        - script_expected = 2
        - script_matched = 2 (deployed by utilities_plugin)
        - script_ok = True
        - "Scripts verified (2/2)" appears in stdout
        """
        _, _, stdout = installed_console_script
        scripts_lines = [
            line for line in stdout.splitlines() if "Scripts verified" in line
        ]
        assert scripts_lines, (
            f"No 'Scripts verified' line in install stdout.\n--- stdout ---\n{stdout}"
        )
        # The expected line: "    ✅ Scripts verified (2/2)"
        assert any("(2/2)" in line for line in scripts_lines), (
            "Scripts verified count is not (2/2). Lines found:\n"
            + "\n".join(f"  {line.strip()}" for line in scripts_lines)
            + "\n\nThis is the v3.12.1 Bug #2 regression: either the wheel did "
            "not ship utility scripts (Bug #1), the verifier rejects "
            "zero-expected (Bug #2), or utilities_plugin failed to deploy them.\n"
            f"--- full stdout ---\n{stdout}"
        )


@pytest.mark.e2e
class TestPyPIShapeDoctorChain:
    """Locks Bug #4: doctor must report all checks passing on a clean install.

    Check count: was 7 in v3.12; v3.14 added an 8th (DensityCheck per D6/D12).
    The test asserts on the literal "{N}/{N} checks passed, 0 failed" pattern
    rather than a fixed count — survives future check additions.

    `nwave-ai doctor` is read-only (nwave_ai/doctor/runner.py writes nothing),
    so a single session-scoped subprocess capture is sufficient for all
    assertion contracts.  Both original assertion blocks are preserved verbatim.
    """

    @pytest.fixture(scope="session")
    def _doctor_stdout(self, installed_console_script) -> str:
        """Run `nwave-ai doctor` exactly once and return stdout.

        Session-scoped: amortizes the 30-120s subprocess across all
        TestPyPIShapeDoctorChain assertions.  doctor/runner.py is read-only
        (no writes between calls), so a single capture is safe.
        """
        venv, fake_home, _ = installed_console_script
        console_script = venv / "bin" / "nwave-ai"
        env = {
            "HOME": str(fake_home),
            "PATH": f"{venv / 'bin'}:{os.environ.get('PATH', '')}",
        }
        code, out = _run(
            [str(console_script), "doctor"],
            env=env,
            timeout=120,
        )
        assert code == 0, (
            f"`nwave-ai doctor` failed (exit {code}).\n--- stdout ---\n{out}"
        )
        return out

    def test_doctor_all_checks_pass(self, _doctor_stdout: str) -> None:
        """`nwave-ai doctor` MUST exit 0 and report all checks passing.

        Merges contracts from former test_doctor_reports_all_passing (exit code,
        N/N pattern, negative markers) and test_doctor_framework_files_passes
        (framework_files line starts with ✅).  Invokes the CONSOLE SCRIPT (not
        `python -m`) so a regression in [project.scripts] surfaces here too.
        """
        import re

        out = _doctor_stdout

        # Match N/N where total >= 7 (Bug #4 floor) and 0 failures.
        match = re.search(r"(\d+)/(\d+) checks passed, 0 failed", out)
        assert match is not None, (
            "Doctor did not report '<N>/<N> checks passed, 0 failed'. "
            "This is the v3.12.1 Bug #4 regression: doctor's framework_files "
            "check still requires stale REQUIRED_DIRS entries that v2.8.0 "
            f"removed.\n--- stdout ---\n{out}"
        )
        passed, total = int(match.group(1)), int(match.group(2))
        assert passed == total and total >= 7, (
            f"Doctor reported {passed}/{total} checks passed (need N/N where N>=7). "
            f"Bug #4 floor not met.\n--- stdout ---\n{out}"
        )
        # Negative checks: nothing must indicate failure
        for forbidden in (
            "1 failed",
            "2 failed",
            "commands/: missing",
            "⚠️",
        ):
            assert forbidden not in out, (
                f"Doctor stdout contains forbidden marker {forbidden!r}.\n"
                f"--- stdout ---\n{out}"
            )
        # Bug #4 specifically: framework_files check is ✅ (not ⚠️).
        # Pre-fix: `commands/: missing` warning. Post-fix: silent pass.
        framework_lines = [
            line for line in out.splitlines() if "framework_files" in line
        ]
        assert framework_lines, (
            f"No framework_files line in doctor output.\n--- stdout ---\n{out}"
        )
        for line in framework_lines:
            assert line.startswith("✅"), (
                f"framework_files check did not pass: {line!r}\n"
                f"--- full stdout ---\n{out}"
            )
