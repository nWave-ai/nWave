#!/usr/bin/env python3
"""
Shell Script Prevention Hook

Prevents shell, PowerShell, and batch scripts from being committed.
This ensures a pure Python codebase for cross-platform compatibility.

Usage:
    python scripts/hooks/prevent_shell_scripts.py

Exit codes:
    0 - No prohibited scripts found
    1 - Prohibited scripts detected, commit blocked
"""

import subprocess
import sys
from pathlib import Path


# Prohibited script extensions and their descriptions
PROHIBITED_EXTENSIONS = {
    ".sh": "Shell script (Bash/sh)",
    ".bash": "Bash script",
    ".zsh": "Zsh script",
    ".ksh": "Korn shell script",
    ".csh": "C shell script",
    ".ps1": "PowerShell script",
    ".bat": "Windows batch file",
    ".cmd": "Windows command script",
}


def get_staged_files():
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except subprocess.CalledProcessError:
        return []


def check_for_shell_scripts(staged_files):
    """
    Check if any staged files are prohibited script types.

    Returns:
        List of (filepath, script_type) tuples for prohibited files
    """
    prohibited_files = []

    for filepath in staged_files:
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext in PROHIBITED_EXTENSIONS:
            prohibited_files.append((filepath, PROHIBITED_EXTENSIONS[ext]))

    return prohibited_files


def main():
    print("Checking for prohibited shell scripts...")

    staged_files = get_staged_files()

    if not staged_files:
        print("✓ No staged files to check")
        return 0

    prohibited = check_for_shell_scripts(staged_files)

    if not prohibited:
        print("✓ No prohibited shell scripts detected")
        return 0

    # Prohibited scripts found - block commit
    print("\n" + "=" * 80)
    print("❌ COMMIT BLOCKED: Prohibited shell scripts detected")
    print("=" * 80)
    print()
    print(
        "This project maintains a pure Python codebase for cross-platform compatibility."
    )
    print("Shell scripts introduce platform-specific issues:")
    print("  • Line ending problems (LF vs CRLF)")
    print("  • Syntax differences (bash vs sh vs zsh)")
    print("  • Platform limitations (not available on Windows)")
    print("  • Additional tooling (shellcheck, etc.)")
    print()
    print("PROHIBITED FILES:")
    for filepath, script_type in prohibited:
        print(f"  • {filepath} ({script_type})")
    print()
    print("REQUIRED ACTION:")
    print("  1. Convert script to Python (.py)")
    print("  2. Use subprocess module for shell commands if needed")
    print("  3. Ensure cross-platform compatibility (pathlib, os module)")
    print()
    print("EXAMPLES:")
    print('  • Instead of: echo "Hello" > file.txt')
    print('    Use Python: Path("file.txt").write_text("Hello")')
    print("  • Instead of: find . -name '*.py'")
    print("    Use Python: Path('.').glob('**/*.py')")
    print()
    print("OVERRIDE (use only with explicit user approval):")
    print("  git commit --no-verify")
    print()
    print("=" * 80)

    return 1


if __name__ == "__main__":
    sys.exit(main())
