#!/usr/bin/env python3
"""Code Formatter Availability Check Hook

Detects when code formatter tools are not available.
Provides installation instructions and alternatives.
"""

import shutil
import subprocess
import sys


# Color codes
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def get_staged_python_files():
    """Get list of staged Python files.

    Returns:
        list: List of Python file paths, or empty list if none
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            check=True,
            capture_output=True,
            text=True,
        )
        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        python_files = [f for f in files if f.endswith(".py")]
        return python_files
    except subprocess.CalledProcessError:
        return []


def formatter_available(formatter: str) -> bool:
    """Return True if the formatter is runnable.

    The dev workflow manages tools through uv, so they live in the project
    `.venv` rather than on PATH. Prefer `uv run <tool> --version`; fall back to a
    bare PATH lookup for activated-venv / globally installed setups.
    """
    if shutil.which("uv"):
        try:
            subprocess.run(
                ["uv", "run", formatter, "--version"],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
    return shutil.which(formatter) is not None


def main():
    """Check code formatter availability."""
    print(f"{BLUE}Checking code formatter availability...{NC}")

    # Check if any Python files are being staged
    python_files = get_staged_python_files()

    if not python_files:
        print(f"{BLUE}No Python files to check{NC}")
        return 0

    # Formatters to check
    formatters = ["ruff", "mypy"]
    missing_formatters = []

    # Check each formatter
    for formatter in formatters:
        if not formatter_available(formatter):
            missing_formatters.append(formatter)

    if not missing_formatters:
        print(f"{GREEN}All required formatters available{NC}")
        return 0

    # Formatters are missing
    print()
    print(f"{RED}FORMATTER NOT FOUND ERROR{NC}")
    print()
    print(f"{RED}Missing formatters:{NC}")
    for formatter in missing_formatters:
        print(f"  - {formatter}")
    print()

    print(f"{YELLOW}These are dev dependencies. Set them up with:{NC}")
    print("  uv sync")
    print("  uv run pre-commit run --all-files")
    print()

    print(f"{RED}COMMIT BLOCKED: Formatter tools not available{NC}")
    print(f"{YELLOW}Emergency bypass: git commit --no-verify{NC}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
