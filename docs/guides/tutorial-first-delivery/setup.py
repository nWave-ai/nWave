#!/usr/bin/env python3
"""Setup for Tutorial 1: Your First Delivery.

Creates the tutorial-ascii-art starter project from scratch — empty
implementation, three failing acceptance tests, a 4x4 PPM fixture, a
venv with pytest, and an initial git commit. Self-contained: no
network access required, no external repo dependency.

Run from outside the nwave-dev repo (e.g. ``cd $(mktemp -d)`` first).
See manual-setup.md for the same steps written as prose.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_DIR = Path("tutorial-ascii-art")

PYPROJECT_TOML = """\
[project]
name = "ascii-art"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
"""

GITIGNORE = """\
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mutmut-cache/
docs/feature/
docs/evolution/
.nwave/
.develop-progress.json
"""

TEST_ASCII_ART_PY = '''\
"""Acceptance tests for image-to-ASCII converter.

These 3 tests define the complete feature contract.
nWave will implement the code to make them pass.
"""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_converts_image_to_ascii_with_correct_width():
    """Given a PPM image
    When I convert it to ASCII art with width=20
    Then every line of output is exactly 20 characters wide."""
    from ascii_art import image_to_ascii

    result = image_to_ascii(FIXTURES / "diagonal.ppm", width=20)
    lines = result.strip().split("\\n")

    assert len(lines) > 0
    assert all(len(line) == 20 for line in lines)


def test_output_uses_only_density_characters():
    """Given a PPM image
    When I convert it to ASCII art
    Then the output contains only characters from the density ramp."""
    from ascii_art import image_to_ascii

    DENSITY = " .:-=+*#%@"
    result = image_to_ascii(FIXTURES / "diagonal.ppm", width=10)

    for char in result:
        assert char in DENSITY or char == "\\n"


def test_bright_pixels_produce_dense_characters():
    """Given an image with a white diagonal on black background
    When I convert it to ASCII art
    Then bright pixels map to dense characters like @ or #
    And dark pixels map to sparse characters like space or dot."""
    from ascii_art import image_to_ascii

    result = image_to_ascii(FIXTURES / "diagonal.ppm", width=4)
    lines = result.strip().split("\\n")

    # The diagonal image has white pixels on the diagonal
    # First line: bright pixel at position 0, dark elsewhere
    first_line = lines[0]
    assert first_line[0] in "#%@"  # bright pixel -> dense char
    assert first_line[-1] in " .:"  # dark pixel -> sparse char
'''

DIAGONAL_PPM = """\
P3
4 4
255
255 255 255  0 0 0  0 0 0  0 0 0
0 0 0  255 255 255  0 0 0  0 0 0
0 0 0  0 0 0  255 255 255  0 0 0
0 0 0  0 0 0  0 0 0  255 255 255
"""


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
    (PROJECT_DIR / "src" / "ascii_art").mkdir(parents=True)
    (PROJECT_DIR / "tests" / "fixtures").mkdir(parents=True)

    # Step 2: package init files (empty — ascii_art/__init__.py is what nWave fills in)
    (PROJECT_DIR / "src" / "__init__.py").touch()
    (PROJECT_DIR / "src" / "ascii_art" / "__init__.py").touch()
    (PROJECT_DIR / "tests" / "__init__.py").touch()

    # Step 3: configuration + tests + fixture
    (PROJECT_DIR / "pyproject.toml").write_text(PYPROJECT_TOML)
    (PROJECT_DIR / ".gitignore").write_text(GITIGNORE)
    (PROJECT_DIR / "tests" / "test_ascii_art.py").write_text(TEST_ASCII_ART_PY)
    (PROJECT_DIR / "tests" / "fixtures" / "diagonal.ppm").write_text(DIAGONAL_PPM)

    # Step 4: virtualenv + pytest
    venv_dir = PROJECT_DIR / ".venv"
    venv.create(venv_dir, with_pip=True)
    subprocess.run(
        [str(_venv_pip(venv_dir)), "install", "--quiet", "pytest"],
        check=True,
    )

    # Step 5: git init + initial commit (nWave uses commits to track TDD progress)
    _git("init", "--quiet", cwd=PROJECT_DIR)
    _git("add", "-A", cwd=PROJECT_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        "feat: ascii-art starter project (empty implementation, 3 failing tests)",
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
        f"  pytest tests/ -v             # confirm 3 tests fail (expected)\n\n"
        f'Then open Claude Code and run /nw-deliver "Image-to-ASCII art converter using PPM format"\n'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
