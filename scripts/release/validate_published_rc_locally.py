#!/usr/bin/env python3
"""Local mirror of CI Validate Published RC — install-behaviour subset.

Runs the same `nwave-ai install` behaviour the Stage 2 RC release pipeline
validates, but skips the wheel build/publish round-trip. Exercises the two
install-time failure modes that have broken recent RCs:

  1. issue #41 — patcher leaves the wheel without the nwave-ai console
     script entry. Mirrored via a direct call to patch_pyproject + grep on
     the patched [project.scripts] section.
  2. reviewer_signing_plugin EROFS — install crashes when the project dir
     is read-only. Mirrored via running `python -m nwave_ai.cli install
     --yes` from a chmod 555 .nwave/ subdir under a fake HOME.

Exit codes:
    0  — both checks pass
    1  — either check fails

Usage:
    pipenv run python scripts/release/validate_published_rc_locally.py

Runtime: ~10-20s. Catches both bugs above instantly.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=cwd, env=env, check=False, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"    exit={result.returncode}")
        print(f"    stdout: {result.stdout[-2000:]}")
        print(f"    stderr: {result.stderr[-2000:]}")
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


def _check_entry_point_regression(workdir: Path) -> None:
    """Issue #41 — patcher must merge nwave-ai into [project.scripts]."""
    print("[1/2] Check patcher emits nwave-ai console script (issue #41 guard)...")
    src_pyproject = _REPO_ROOT / "pyproject.toml"
    out_pyproject = workdir / "patched.toml"
    _run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "release" / "patch_pyproject.py"),
            "--input",
            str(src_pyproject),
            "--output",
            str(out_pyproject),
            "--target-name",
            "nwave-ai",
            "--target-version",
            "0.0.0.dev0",
        ]
    )
    content = out_pyproject.read_text()
    if "[project.scripts]" not in content:
        raise RuntimeError(
            "FAIL (issue #41): [project.scripts] section missing from patched pyproject."
        )
    # Match `nwave-ai = "..."` inside [project.scripts]
    scripts_block = re.search(r"\[project\.scripts\]\n((?:[^\[].*\n?)+)", content)
    if scripts_block is None or 'nwave-ai = "' not in scripts_block.group(1):
        raise RuntimeError(
            f"FAIL (issue #41): nwave-ai entry NOT in [project.scripts]:\n"
            f"{scripts_block.group(1) if scripts_block else '(no block found)'}"
        )
    print("    ✅ patched pyproject contains nwave-ai console script entry")


def _check_install_under_readonly_project(workdir: Path) -> None:
    """reviewer_signing_plugin must soft-skip on EROFS-class errors.

    Mirrors the CI failure: /src is a read-only container mount, so the
    project-level .nwave/secrets/ cannot be created. The install must
    succeed; soft-skip plugins must absorb the OSError.
    """
    print("[2/2] Run `nwave-ai install --yes` from read-only project dir...")
    project = workdir / "ro-project"
    project.mkdir()
    nwave_dir = project / ".nwave"
    nwave_dir.mkdir()
    nwave_dir.chmod(0o555)  # read-only
    fake_home = workdir / "fake-home"
    fake_home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    # Drop NWAVE_REVIEWER_SIGNING_KEY so the file-provision path is exercised
    env.pop("NWAVE_REVIEWER_SIGNING_KEY", None)
    try:
        _run(
            [sys.executable, "-m", "nwave_ai.cli", "install", "--yes"],
            cwd=project,
            env=env,
        )
    finally:
        nwave_dir.chmod(0o755)
    claude_dir = fake_home / ".claude"
    agents_nw = claude_dir / "agents" / "nw"
    settings = claude_dir / "settings.json"
    if not agents_nw.exists():
        raise RuntimeError(f"FAIL: {agents_nw} not provisioned by install.")
    if not settings.exists():
        raise RuntimeError(f"FAIL: {settings} not written by install.")
    print(
        f"    ✅ install succeeded under read-only project; "
        f"{claude_dir}/{{agents/nw, settings.json}} both provisioned"
    )


def main() -> int:
    print("=" * 70)
    print("Local mirror of CI Validate Published RC (install-behaviour subset)")
    print("=" * 70)
    with tempfile.TemporaryDirectory(prefix="nwave-rc-local-") as workdir_str:
        workdir = Path(workdir_str)
        try:
            _check_entry_point_regression(workdir)
            _check_install_under_readonly_project(workdir)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ VALIDATION FAILED: {e}")
            return 1
        except RuntimeError as e:
            print(f"\n❌ VALIDATION FAILED: {e}")
            return 1
    print("\n" + "=" * 70)
    print("✅ BOTH CHECKS PASSED — install path is RC-ready")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
