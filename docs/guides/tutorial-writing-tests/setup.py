#!/usr/bin/env python3
"""Setup for Tutorial 2: Writing Acceptance Tests That Guide Delivery.

Creates an empty md-converter Python project with pytest, git init, and
an initial commit. Idempotent: a second run exits cleanly; pass --force
to wipe and recreate.

Run from outside the nwave-dev repo (e.g. ``cd $(mktemp -d)`` first).
See manual-setup.md for the same steps written as prose.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_DIR = Path("md-converter")

PYPROJECT_TOML = """\
[project]
name = "md-converter"
version = "0.1.0"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
"""

GITIGNORE = ".venv/\n"


def _venv_pip(venv_dir: Path) -> Path:
    """Return the path to the venv's pip, handling Windows vs POSIX layout."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def _git(*args: str, cwd: Path) -> None:
    """Run git with deterministic author info (so the test environment works)."""
    subprocess.run(
        [
            "git",
            # bootstrap repo: disable the contributor's global git hooks
            # (e.g. templateDir-injected pre-commit/prepare-commit-msg) so the
            # demo commit doesn't fail on a missing .pre-commit-config.yaml
            "-c",
            "core.hooksPath=.disabled-git-hooks",
            "-c",
            "user.email=tutorial@nwave.ai",
            "-c",
            "user.name=tutorial",
            *args,
        ],
        cwd=str(cwd),
        check=True,
    )


def main() -> int:
    force = "--force" in sys.argv[1:]

    if force and PROJECT_DIR.exists():
        shutil.rmtree(PROJECT_DIR)

    if PROJECT_DIR.exists():
        print(f"{PROJECT_DIR} already exists. Run with --force to recreate.")
        return 0

    # Step 1: project skeleton
    (PROJECT_DIR / "src" / "md_converter").mkdir(parents=True)
    (PROJECT_DIR / "tests").mkdir()
    (PROJECT_DIR / "src" / "md_converter" / "__init__.py").touch()
    (PROJECT_DIR / "tests" / "__init__.py").touch()

    # Step 2: pyproject.toml and .gitignore
    (PROJECT_DIR / "pyproject.toml").write_text(PYPROJECT_TOML)
    (PROJECT_DIR / ".gitignore").write_text(GITIGNORE)

    # Step 3: virtualenv + pytest (don't activate — activation doesn't persist
    # past script exit)
    venv_dir = PROJECT_DIR / ".venv"
    venv.create(venv_dir, with_pip=True)
    subprocess.run(
        [str(_venv_pip(venv_dir)), "install", "--quiet", "pytest"],
        check=True,
    )

    # Step 4: git init + initial commit (nWave uses commits to track TDD progress)
    _git("init", "--quiet", cwd=PROJECT_DIR)
    _git("add", "-A", cwd=PROJECT_DIR)
    _git("commit", "--quiet", "-m", "chore: initial project structure", cwd=PROJECT_DIR)

    activate_hint = (
        r".venv\Scripts\activate"
        if sys.platform == "win32"
        else "source .venv/bin/activate"
    )
    print(
        f"\nSetup complete. {PROJECT_DIR} ready.\n\n"
        f"Next steps:\n"
        f"  cd {PROJECT_DIR}\n"
        f"  {activate_hint}\n\n"
        f"You're ready to start writing your first acceptance test (Step 2 of the tutorial).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
