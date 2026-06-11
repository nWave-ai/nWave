#!/usr/bin/env python3
"""Setup for Tutorial 11: Safe Refactoring with Mikado.

Creates the messy expense-tracker starter project — intentionally smelly
code with passing tests, ready to refactor.

Run from outside the nwave-dev repo (e.g. ``cd $(mktemp -d)`` first).
See manual-setup.md for the same steps written as prose.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_DIR = Path("expense-tracker")

EXPENSES_PY = """\
# src/expenses.py -- intentionally messy, do not clean up manually
import json
from datetime import datetime

class ExpenseManager:

    def __init__(self):
        self.expenses = []
        self.tax_rate = 0.21  # hardcoded tax rate
        self.currency = "USD"  # hardcoded currency

    def add_expense(self, amount, category, description=""):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if category not in ["food", "transport", "office", "other"]:
            raise ValueError("Invalid category")
        expense = {
            "amount": amount,
            "category": category,
            "description": description,
            "date": datetime.now().isoformat(),
            "amount_with_tax": round(amount * (1 + 0.21), 2),  # duplicated tax rate
        }
        self.expenses.append(expense)
        return expense

    def get_total(self):
        total = 0
        for e in self.expenses:
            total += e["amount"]
        return total

    def get_total_with_tax(self):
        total = 0
        for e in self.expenses:
            total += e["amount"] * (1 + 0.21)  # duplicated tax rate again
        return round(total, 2)

    def get_report(self):
        lines = []
        lines.append("=== Expense Report ===")
        lines.append(f"Currency: USD")  # hardcoded currency again
        for e in self.expenses:
            lines.append(f"  {e['category']:12s} ${e['amount']:.2f}  {e['description']}")
        lines.append(f"  {'SUBTOTAL':12s} ${self.get_total():.2f}")
        lines.append(f"  {'TAX (21%)':12s} ${self.get_total() * 0.21:.2f}")  # duplicated
        lines.append(f"  {'TOTAL':12s} ${self.get_total_with_tax():.2f}")
        lines.append("=" * 22)
        return "\\n".join(lines)

    def save_to_file(self, path):
        with open(path, "w") as f:
            json.dump(self.expenses, f, indent=2)

    def load_from_file(self, path):
        with open(path) as f:
            self.expenses = json.load(f)

    def get_by_category(self, category):
        result = []
        for e in self.expenses:
            if e["category"] == category:
                result.append(e)
        return result

    def get_category_total(self, category):
        total = 0
        for e in self.expenses:
            if e["category"] == category:
                total += e["amount"]
        return total

    def get_category_total_with_tax(self, category):
        total = 0
        for e in self.expenses:
            if e["category"] == category:
                total += e["amount"] * (1 + 0.21)  # duplicated tax rate yet again
        return round(total, 2)
"""

TEST_EXPENSES_PY = """\
# tests/test_expenses.py
import pytest
from src.expenses import ExpenseManager

@pytest.fixture
def manager():
    em = ExpenseManager()
    em.add_expense(10.00, "food", "Lunch")
    em.add_expense(25.50, "transport", "Taxi")
    em.add_expense(5.00, "food", "Coffee")
    return em

def test_add_expense(manager):
    assert len(manager.expenses) == 3

def test_add_expense_negative_raises():
    em = ExpenseManager()
    with pytest.raises(ValueError, match="positive"):
        em.add_expense(-5, "food")

def test_add_expense_invalid_category():
    em = ExpenseManager()
    with pytest.raises(ValueError, match="Invalid category"):
        em.add_expense(10, "vacation")

def test_get_total(manager):
    assert manager.get_total() == 40.50

def test_get_total_with_tax(manager):
    # The mathematical answer is 49.005; IEEE 754 rounding can land on
    # either 49.00 or 49.01 depending on the platform — use approx to be robust.
    assert manager.get_total_with_tax() == pytest.approx(49.005, abs=0.01)

def test_get_by_category(manager):
    food = manager.get_by_category("food")
    assert len(food) == 2

def test_get_category_total(manager):
    assert manager.get_category_total("food") == 15.00

def test_get_category_total_with_tax(manager):
    assert manager.get_category_total_with_tax("food") == 18.15

def test_get_report(manager):
    report = manager.get_report()
    assert "Expense Report" in report
    assert "TOTAL" in report
    # Compute the expected string dynamically — the report formats whatever
    # get_total_with_tax() returns (49.00 or 49.01 depending on float rounding).
    assert f"${manager.get_total_with_tax():.2f}" in report
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
    (PROJECT_DIR / "src" / "expenses.py").write_text(EXPENSES_PY)
    (PROJECT_DIR / "tests" / "test_expenses.py").write_text(TEST_EXPENSES_PY)
    (PROJECT_DIR / "conftest.py").write_text(CONFTEST_PY)
    (PROJECT_DIR / ".gitignore").write_text(GITIGNORE)

    # Step 3: virtualenv + pytest
    venv_dir = PROJECT_DIR / ".venv"
    venv.create(venv_dir, with_pip=True)
    subprocess.run(
        [str(_venv_pip(venv_dir)), "install", "--quiet", "pytest"],
        check=True,
    )

    # Step 4: git init + initial commit (the messy starting state)
    _git("init", "--quiet", cwd=PROJECT_DIR)
    _git("add", "-A", cwd=PROJECT_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        "feat: messy expense tracker (starting point for refactoring)",
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
        f"  pytest tests/ -v --no-header   # all 9 tests should pass\n\n"
        f"You're ready to start the refactoring tutorial.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
