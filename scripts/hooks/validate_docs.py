#!/usr/bin/env python3
"""Documentation Version Validation Hook

Ensures documentation versions are synchronized.
"""

import os
import subprocess
import sys
from pathlib import Path


# Windows color support detection
def supports_color() -> bool:
    """Check if the terminal supports ANSI color codes."""
    # Check for NO_COLOR environment variable (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False
    # Check for FORCE_COLOR environment variable
    if os.environ.get("FORCE_COLOR"):
        return True
    # Windows: check for ANSICON, ConEmu, or Windows Terminal
    if sys.platform == "win32":
        return (
            os.environ.get("ANSICON") is not None
            or os.environ.get("WT_SESSION") is not None  # Windows Terminal
            or os.environ.get("ConEmuANSI") == "ON"
            or os.environ.get("TERM_PROGRAM") == "vscode"
        )
    # Unix-like: check if stdout is a tty
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# Color codes (disabled on unsupported terminals)
if supports_color():
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"
else:
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    NC = ""


def clear_git_environment():
    """Clear git environment variables that pre-commit sets.

    These can cause git commands to fail or behave unexpectedly.
    """
    git_vars = ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"]
    for var in git_vars:
        os.environ.pop(var, None)


def get_repo_root() -> Path:
    """Get the git repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return Path(result.stdout.strip())
    except subprocess.SubprocessError:
        # Fallback to current directory if not in a git repo
        return Path.cwd()
    except FileNotFoundError:
        # Git not available
        return Path.cwd()


def main():
    """Run documentation version validation."""
    clear_git_environment()

    print(f"{BLUE}Running documentation version validation...{NC}")

    # Get repository root for proper path resolution
    repo_root = get_repo_root()

    # Check if validation infrastructure exists
    dependency_map = repo_root / ".dependency-map.yaml"
    validation_script = (
        repo_root / "scripts" / "validation" / "validate-documentation-versions.py"
    )

    if not dependency_map.exists():
        print(
            f"{YELLOW}Warning: .dependency-map.yaml not found, skipping version validation{NC}"
        )
        return 0

    if not validation_script.exists():
        print(
            f"{YELLOW}Warning: validation script not found, skipping version validation{NC}"
        )
        return 0

    # Use sys.executable for cross-platform compatibility (Windows uses 'python', Unix uses 'python3')
    python_cmd = sys.executable

    # Run validation
    try:
        result = subprocess.run(
            [python_cmd, str(validation_script)],
            check=False,
            capture_output=False,
            timeout=60,
        )

        if result.returncode == 0:
            print(f"{GREEN}Documentation version validation passed{NC}")
            return 0
        elif result.returncode == 2:
            print(
                f"{RED}Configuration error in version validation{NC}", file=sys.stderr
            )
            print(f"{RED}Check .dependency-map.yaml for errors{NC}", file=sys.stderr)
            return 1
        else:
            # Error report already printed by Python script
            print(file=sys.stderr)
            print(
                f"{YELLOW}Emergency bypass: git commit --no-verify{NC}", file=sys.stderr
            )
            return 1
    except subprocess.SubprocessError as e:
        print(f"{RED}Unexpected error running validation: {e}{NC}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"{RED}Unexpected error running validation: {e}{NC}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
