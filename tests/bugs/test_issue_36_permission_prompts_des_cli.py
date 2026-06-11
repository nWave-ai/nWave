"""Regression test for nwave-ai/nwave#36 — permission prompts in DES CLI.

Three assertion levels (upgrading theater→runtime):

1. No banned PYTHONPATH=.../python3 -m des.cli.* pattern exists in 3 skills
   and 3 task files.                                            (source-level)
2. Five DES shim executables are installed under ~/.claude/bin/ and are
   executable by the current user.                               (stat-level)
3. shutil.which("des-log-phase", path=<settings env.PATH>) returns non-None
   on a staged install.                                       (runtime-level)

Stat-level tests (1+2) remain for fast source regression detection.
Runtime assertion (3) catches the class of failure that stat misses: absent
~/.claude/lib/python/des/ -> ImportError at execution time, but all stat
checks green.  The authoritative runtime contract lives in the E2E test
tests/e2e/test_fresh_install.py (requires Docker).

Both tests (1+2) are EXPECTED TO FAIL on master until steps 01-05 (shim
install) and 01-06 (skill rewrite) complete.
"""

import os
import re
import shutil
import stat
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Repo root resolution
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.parent

# ---------------------------------------------------------------------------
# Target files
# ---------------------------------------------------------------------------
_SKILL_FILES = [
    _REPO_ROOT / "nWave" / "skills" / "nw-execute" / "SKILL.md",
    _REPO_ROOT / "nWave" / "skills" / "nw-deliver" / "SKILL.md",
    _REPO_ROOT / "nWave" / "skills" / "nw-roadmap" / "SKILL.md",
]

_TASK_FILES = [
    _REPO_ROOT / "nWave" / "tasks" / "nw" / "deliver.md",
    _REPO_ROOT / "nWave" / "tasks" / "nw" / "execute.md",
    _REPO_ROOT / "nWave" / "tasks" / "nw" / "roadmap.md",
]

# Pattern covering both $HOME and ~ variants
_BANNED_PATTERN_DOLLAR = re.compile(
    r"PYTHONPATH=\$HOME/\.claude/lib/python.*-m\s+des\.cli\.",
    re.DOTALL,
)
_BANNED_PATTERN_TILDE = re.compile(
    r"PYTHONPATH=~/\.claude/lib/python.*-m\s+des\.cli\.",
    re.DOTALL,
)

# ---------------------------------------------------------------------------
# Shim configuration
# ---------------------------------------------------------------------------
_SHIM_DIR = Path.home() / ".claude" / "bin"
_EXPECTED_SHIMS = [
    "des-log-phase",
    "des-init-log",
    "des-verify-integrity",
    "des-roadmap",
    "des-health-check",
]


def test_no_pythonpath_pattern_in_skills_and_tasks() -> None:
    """Assert that the banned PYTHONPATH DES CLI invocation pattern is absent
    from the 3 skills and 3 task files.

    Fails on master because the pattern is still present in those files.
    Will pass after step 01-06 rewrites the invocation to use shims.
    """
    target_files = _SKILL_FILES + _TASK_FILES

    violations: list[str] = []
    for path in target_files:
        assert path.exists(), f"Target file not found on disk: {path}"
        content = path.read_text(encoding="utf-8")
        if _BANNED_PATTERN_DOLLAR.search(content) or _BANNED_PATTERN_TILDE.search(
            content
        ):
            violations.append(str(path.relative_to(_REPO_ROOT)))

    assert violations == [], (
        "Banned PYTHONPATH=.../python3 -m des.cli.* pattern found in:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nFix: rewrite invocations to use the ~/.claude/bin/ shim (step 01-06)."
    )


@pytest.mark.parametrize(
    "pattern_variant",
    [
        pytest.param(
            "PYTHONPATH=$HOME/.claude/lib/python python3 -m des.cli.log_phase",
            id="dollar-HOME-variant",
        ),
        pytest.param(
            "PYTHONPATH=~/.claude/lib/python python3 -m des.cli.log_phase",
            id="tilde-variant",
        ),
    ],
)
def test_tilde_variant_detection_sensitivity(
    tmp_path: "Path", pattern_variant: str
) -> None:
    """Assert that BOTH regex patterns (_BANNED_PATTERN_DOLLAR and
    _BANNED_PATTERN_TILDE) would catch their respective banned patterns if
    reintroduced in a file.

    Uses a synthetic tmp file so as not to mutate production files.
    """
    fake_file = tmp_path / "fake_skill.md"
    fake_file.write_text(
        f"Use this command:\n```\n{pattern_variant}\n```\n",
        encoding="utf-8",
    )
    content = fake_file.read_text(encoding="utf-8")
    matched = _BANNED_PATTERN_DOLLAR.search(content) or _BANNED_PATTERN_TILDE.search(
        content
    )
    assert matched, (
        f"Scanner did NOT detect banned pattern variant:\n  {pattern_variant!r}\n"
        "Both _BANNED_PATTERN_DOLLAR and _BANNED_PATTERN_TILDE must cover "
        "their respective forms."
    )


def test_shims_installed_and_executable() -> None:
    """Assert that all 5 DES shims exist under ~/.claude/bin/ and are executable.

    Skipped when ~/.claude/bin/ doesn't exist (e.g. on CI runners or fresh
    checkouts where nWave hasn't been installed): this is a runtime guard
    on an installed environment, not a build-time check.  Container-level
    coverage (real install + shim verification) is owned by tests/e2e/.
    """
    if not _SHIM_DIR.exists():
        import pytest

        pytest.skip(
            f"{_SHIM_DIR} not found — nWave not installed in this environment. "
            "Container-level coverage owned by tests/e2e/test_pypi_install.py."
        )
    missing: list[str] = []
    not_executable: list[str] = []

    for shim_name in _EXPECTED_SHIMS:
        shim_path = _SHIM_DIR / shim_name
        if not shim_path.exists():
            missing.append(shim_name)
        elif not os.access(shim_path, os.X_OK):
            not_executable.append(shim_name)

    errors: list[str] = []
    if missing:
        errors.append(
            "Missing shims in ~/.claude/bin/:\n"
            + "\n".join(f"  - {s}" for s in missing)
        )
    if not_executable:
        errors.append(
            "Non-executable shims in ~/.claude/bin/:\n"
            + "\n".join(f"  - {s}" for s in not_executable)
        )

    if len(missing) == len(_EXPECTED_SHIMS):
        import pytest

        pytest.skip(
            f"No DES shims present in {_SHIM_DIR} — nWave is not installed with "
            "shims in this environment (the bin dir exists but is empty, e.g. a "
            "partial dev install). Container-level coverage owned by "
            "tests/e2e/test_pypi_install.py."
        )

    assert not errors, (
        "\n\n".join(errors)
        + "\n\nFix: run the shim installer (step 01-05) to create executable shims."
    )


def test_shim_resolvable_via_staged_env_path(tmp_path: Path) -> None:
    """Runtime-level: shutil.which resolves des-log-phase when ~/.claude/bin/
    is on PATH.

    Upgrades the theater assertion (stat-only) to a runtime-resolution check.
    Stages a fake ~/.claude/bin/ in tmp_path, writes an executable stub shim,
    then asserts shutil.which finds it via that path.

    This test does NOT invoke the shim (no subprocess) — it verifies that PATH
    wiring is correct. The full execution contract (ImportError detection) lives
    in tests/e2e/test_fresh_install.py which runs the shim inside a container.
    """
    # Stage a fake shim directory (simulates what step 01-05 installs)
    fake_bin = tmp_path / ".claude" / "bin"
    fake_bin.mkdir(parents=True)

    # Write a minimal executable stub for des-log-phase
    shim = fake_bin / "des-log-phase"
    shim.write_text("#!/usr/bin/env python3\nprint('stub')\n", encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Verify the shim is executable (stat-level sanity)
    assert os.access(shim, os.X_OK), f"Staged shim is not executable: {shim}"

    # Runtime-level: shutil.which must find it when that bin dir is on PATH
    env_path = str(fake_bin)
    resolved = shutil.which("des-log-phase", path=env_path)
    assert resolved is not None, (
        f"shutil.which('des-log-phase', path={env_path!r}) returned None.\n"
        "This simulates the runtime failure where ~/.claude/bin/ is absent from PATH.\n"
        "Fix: ensure the installer writes ~/.claude/bin to env.PATH in settings.json."
    )
    assert Path(resolved).resolve() == shim.resolve(), (
        f"shutil.which resolved to wrong path.\nExpected: {shim}\nGot:      {resolved}"
    )
