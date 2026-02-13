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
        if not shutil.which(formatter):
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

    print(f"{YELLOW}Installation Instructions:{NC}")
    print()

    if "ruff" in missing_formatters:
        print("For Ruff (combined formatter, linter, import sorter):")
        print("  pip install ruff")
        print("  # or if using system package manager:")
        print("  # apt install ruff  (Debian/Ubuntu)")
        print("  # brew install ruff (macOS)")
        print()

    if "mypy" in missing_formatters:
        print("For Mypy (type checker):")
        print("  pip install mypy")
        print("  # or if using system package manager:")
        print("  # apt install mypy   (Debian/Ubuntu)")
        print("  # brew install mypy  (macOS)")
        print()

    print(f"{YELLOW}Alternative Formatter Configurations:{NC}")
    print()
    print("If you prefer different tools, alternatives include:")
    print()
    print("  Code Formatters (like Ruff):")
    print("    - Black        : pip install black      (strict formatting)")
    print("    - Autopep8     : pip install autopep8   (PEP 8 compliant)")
    print("    - YAPF         : pip install yapf       (flexible formatting)")
    print()
    print("  Type Checkers (like Mypy):")
    print("    - Pyright      : pip install pyright    (VSCode native)")
    print("    - Pydantic     : pip install pydantic   (runtime validation)")
    print()
    print("Configuration can be updated in .pre-commit-config.yaml")
    print()

    print(f"{YELLOW}Quick setup:{NC}")
    print("  pip install ruff mypy")
    print("  pre-commit run --all-files")
    print()

    print(f"{RED}COMMIT BLOCKED: Formatter tools not available{NC}")
    print(f"{YELLOW}Emergency bypass: git commit --no-verify{NC}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
