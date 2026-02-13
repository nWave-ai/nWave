"""
nWave Target Project Hook Installation Script.

This script installs pre-commit hooks in target projects that use the
nWave development framework. The hooks enforce TDD phase validation
and other quality gates during the development workflow.

Version: 1.0.0
"""

__version__ = "1.0.0"

import argparse
import subprocess
import sys
from pathlib import Path


def check_pre_commit_installed() -> bool:
    """Check if pre-commit is installed and available."""
    try:
        subprocess.run(
            ["pre-commit", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_hooks(project_path: Path, verify_only: bool = False) -> bool:
    """
    Install nWave hooks in the target project.

    Args:
        project_path: Path to the target project
        verify_only: If True, only verify hooks are installed

    Returns:
        True if hooks are installed/verified successfully
    """
    hooks_dir = project_path / ".git" / "hooks"

    if not hooks_dir.exists():
        print(f"Error: Not a git repository: {project_path}")
        return False

    pre_commit_hook = hooks_dir / "pre-commit"

    if verify_only:
        if pre_commit_hook.exists():
            print(f"Pre-commit hook verified at: {pre_commit_hook}")
            return True
        else:
            print("No pre-commit hook found")
            return False

    # Install pre-commit hooks if pre-commit is available
    if check_pre_commit_installed():
        try:
            subprocess.run(
                ["pre-commit", "install"],
                cwd=project_path,
                check=True,
            )
            print("Pre-commit hooks installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install pre-commit hooks: {e}")
            return False
    else:
        print("Warning: pre-commit not installed. Skipping hook installation.")
        return True


def main() -> int:
    """Main entry point for hook installation."""
    parser = argparse.ArgumentParser(
        description="Install nWave development hooks in target project"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify hooks are installed, don't install",
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd(),
        help="Path to target project (default: current directory)",
    )

    args = parser.parse_args()

    success = install_hooks(args.project_path, args.verify_only)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
