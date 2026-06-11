#!/usr/bin/env python3
"""Setup for Tutorial 12: Debugging with 5 Whys.

Creates the csv-processor starter project — buggy code with a CSV
fixture and tests that mostly fail. The user investigates the failure
with /nw-root-why during the tutorial.

Run from outside the nwave-dev repo (e.g. ``cd $(mktemp -d)`` first).
See manual-setup.md for the same steps written as prose.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_DIR = Path("csv-processor")

PROCESSOR_PY = """\
# src/processor.py
# This file has TWO intentional bugs you will discover during the tutorial.
# Don't fix them by reading -- let /nw-root-why walk you through the investigation.


def process_csv(input_text: str) -> list[dict]:
    lines = input_text.strip().split("\\n")
    header = lines[0].split(",")
    results = []
    for line in lines[1:-1]:
        parts = line.split(",")
        if len(parts) != len(header):
            continue
        row = dict(zip(header, parts))
        if not row.get("amount"):
            continue
        row["amount"] = float(row["amount"])
        results.append(row)
    return results


def summarize(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "total": round(sum(r["amount"] for r in rows), 2),
    }
"""

SAMPLE_CSV = """\
name,amount,category
Alice,50.00,food
Bob,30.00,transport
Carol,20.00,food
Dave,,transport
Eve,15.00,office
Frank,10.00,"food, drinks"
Grace,25.00,transport
Heidi,40.00,food
"""

TEST_PROCESSOR_PY = '''\
# tests/test_processor.py
import pytest
from src.processor import process_csv, summarize


SAMPLE_CSV = open("tests/sample.csv").read()


def test_process_csv_row_count():
    """8 rows in CSV, 1 has empty amount, so 7 should remain."""
    rows = process_csv(SAMPLE_CSV)
    assert len(rows) == 7, f"Expected 7 rows, got {len(rows)}: {[r['name'] for r in rows]}"


def test_process_csv_skips_empty_amount():
    rows = process_csv(SAMPLE_CSV)
    names = [r["name"] for r in rows]
    assert "Dave" not in names, "Dave has empty amount and should be skipped"


def test_summarize_total():
    rows = process_csv(SAMPLE_CSV)
    result = summarize(rows)
    assert result["total"] == 190.00, f"Expected 190.00, got {result['total']}"


def test_summarize_count():
    rows = process_csv(SAMPLE_CSV)
    result = summarize(rows)
    assert result["count"] == 7
'''

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

    # Step 2: source files (intentionally buggy)
    (PROJECT_DIR / "src" / "processor.py").write_text(PROCESSOR_PY)
    (PROJECT_DIR / "tests" / "sample.csv").write_text(SAMPLE_CSV)
    (PROJECT_DIR / "tests" / "test_processor.py").write_text(TEST_PROCESSOR_PY)
    (PROJECT_DIR / "conftest.py").write_text(CONFTEST_PY)
    (PROJECT_DIR / ".gitignore").write_text(GITIGNORE)

    # Step 3: virtualenv + pytest
    venv_dir = PROJECT_DIR / ".venv"
    venv.create(venv_dir, with_pip=True)
    subprocess.run(
        [str(_venv_pip(venv_dir)), "install", "--quiet", "pytest"],
        check=True,
    )

    # Step 4: git init + initial commit (the buggy starting state)
    _git("init", "--quiet", cwd=PROJECT_DIR)
    _git("add", "-A", cwd=PROJECT_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        "feat: csv processor with intentional bug (starting point for debugging)",
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
        f"  pytest tests/ -v --no-header   # 3 tests will FAIL — that's the bug you'll investigate\n\n"
        f"You're ready to start the debugging tutorial.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
