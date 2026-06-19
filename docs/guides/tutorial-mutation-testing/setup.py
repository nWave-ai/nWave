#!/usr/bin/env python3
"""Setup for Tutorial 14: Validating Your Test Suite (Mutation Testing).

Creates the mutation-demo starter project — a small calculator with
intentionally weak tests that all pass but miss real bugs. The user
runs mutation testing to expose the gaps.

Run from outside the nwave-dev repo (e.g. ``cd $(mktemp -d)`` first).
See manual-setup.md for the same steps written as prose.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_DIR = Path("mutation-demo")

CALC_PY = '''\
# src/calc.py

def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def discount_price(price: float, percent: float) -> float:
    """Apply a percentage discount. Returns the discounted price."""
    if percent < 0 or percent > 100:
        raise ValueError("Percent must be between 0 and 100")
    return price * (1 - percent / 100)
'''

TEST_CALC_PY = """\
# tests/test_calc.py
from src.calc import add, subtract, multiply, divide, discount_price
import pytest


def test_add():
    result = add(2, 3)
    assert result is not None  # weak: only checks existence


def test_subtract():
    result = subtract(10.0, 4.0)
    assert isinstance(result, float)  # weak: only checks type


def test_multiply():
    result = multiply(3, 4)
    assert result > 0  # weak: many wrong answers are also > 0


def test_divide():
    result = divide(10, 2)
    assert result == 5.0  # strong: checks exact value


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)  # strong: checks error is raised


def test_discount_price():
    result = discount_price(100, 20)
    assert result is not None  # weak: does not check actual price


def test_discount_price_full():
    result = discount_price(100, 100)
    assert result >= 0  # weak: 0 is correct, but so is 50 or 99


def test_discount_invalid_percent():
    with pytest.raises(ValueError):
        discount_price(100, -10)  # strong: checks validation
"""

CONFTEST_PY = 'import sys; sys.path.insert(0, ".")\n'
GITIGNORE = ".venv/\n__pycache__/\n"


def _venv_pip(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def _git(*args: str, cwd: Path) -> None:
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
    (PROJECT_DIR / "src").mkdir(parents=True)
    (PROJECT_DIR / "tests").mkdir()

    # Step 2: source files
    (PROJECT_DIR / "src" / "calc.py").write_text(CALC_PY)
    (PROJECT_DIR / "tests" / "test_calc.py").write_text(TEST_CALC_PY)
    (PROJECT_DIR / "conftest.py").write_text(CONFTEST_PY)
    (PROJECT_DIR / ".gitignore").write_text(GITIGNORE)

    # Step 3: virtualenv + pytest
    venv_dir = PROJECT_DIR / ".venv"
    venv.create(venv_dir, with_pip=True)
    subprocess.run(
        [str(_venv_pip(venv_dir)), "install", "--quiet", "pytest"],
        check=True,
    )

    # Step 4: git init + initial commit
    _git("init", "--quiet", cwd=PROJECT_DIR)
    _git("add", "-A", cwd=PROJECT_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        "feat: calculator with passing tests (starting point for mutation testing)",
        cwd=PROJECT_DIR,
    )

    activate_hint = (
        r".venv\Scripts\activate"
        if sys.platform == "win32"
        else "source .venv/bin/activate"
    )
    print(
        f"\nSetup complete. {PROJECT_DIR} ready.\n\n"
        f"Next steps:\n"
        f"  cd {PROJECT_DIR}\n"
        f"  {activate_hint}\n"
        f"  pytest tests/ -v --no-header   # all 8 tests should pass\n\n"
        f"You're ready to start the mutation testing tutorial.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
