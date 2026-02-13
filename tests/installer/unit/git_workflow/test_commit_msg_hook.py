"""
Unit tests for commit-msg hook installation and behavior.

These tests verify that:
1. Commit-msg hook installation script exists
2. Hook validates conventional commit format
3. Hook rejects invalid commit messages

Cross-platform compatible (Windows, macOS, Linux).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


# Constants for clarity and maintainability
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
SUBPROCESS_TIMEOUT = 10  # seconds


class TestCommitMsgHook:
    """Test commit-msg hook installation and validation."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        current_file = Path(__file__)
        return current_file.parent.parent.parent.parent.parent

    @pytest.fixture
    def git_hooks_dir(self, project_root):
        """Get git hooks directory."""
        return project_root / ".git" / "hooks"

    @pytest.fixture
    def commit_msg_script(self, project_root):
        """Get the Python commit_msg.py script for cross-platform testing."""
        return project_root / "scripts" / "hooks" / "commit_msg.py"

    def _run_hook(self, hook_or_script: Path, msg_file: Path):
        """
        Run the commit-msg hook in a cross-platform way.

        On Unix, we can run the hook file directly if it's executable.
        On Windows, we need to run Python explicitly.
        For consistency, we always use sys.executable to run the Python script.
        """
        # Prefer running the Python script directly with sys.executable
        # This works on all platforms (Windows, macOS, Linux)
        script_dir = hook_or_script.parent
        python_script = script_dir / "commit_msg.py"

        if python_script.exists():
            # Run the Python script directly
            return subprocess.run(
                [sys.executable, str(python_script), str(msg_file)],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
        elif hook_or_script.exists():
            # Fallback: try running the hook file with Python
            return subprocess.run(
                [sys.executable, str(hook_or_script), str(msg_file)],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
        else:
            raise FileNotFoundError(
                f"Neither {python_script} nor {hook_or_script} found"
            )

    def test_commit_msg_hook_exists(self, git_hooks_dir):
        """Verify commit-msg hook is installed.

        This test validates that the commit-msg hook is properly installed.
        CI runs 'pre-commit install --hook-type commit-msg' before tests.
        """
        hook_file = git_hooks_dir / "commit-msg"
        assert hook_file.exists(), "commit-msg hook not found in .git/hooks/"

    def test_commit_msg_hook_is_executable(self, git_hooks_dir):
        """Verify commit-msg hook has execute permissions (Unix) or is readable (Windows)."""
        hook_file = git_hooks_dir / "commit-msg"

        if not hook_file.exists():
            pytest.skip("Hook not installed yet")

        # On Windows, execute permission doesn't apply the same way
        # Just check the file is readable
        if sys.platform == "win32":
            assert os.access(hook_file, os.R_OK), "commit-msg hook is not readable"
        else:
            assert os.access(hook_file, os.X_OK), "commit-msg hook is not executable"

    def test_commit_msg_hook_validates_conventional_format(
        self, commit_msg_script, tmp_path
    ):
        """Verify hook validates conventional commit format."""
        if not commit_msg_script.exists():
            pytest.skip("commit_msg.py script not found")

        # Create temporary commit message file
        msg_file = tmp_path / "commit-msg.txt"
        msg_file.write_text("feat: add user dashboard")

        # Run hook with valid message using cross-platform method
        result = subprocess.run(
            [sys.executable, str(commit_msg_script), str(msg_file)],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )

        assert result.returncode == EXIT_SUCCESS, (
            f"Hook rejected valid commit message. "
            f"stderr: {result.stderr}, stdout: {result.stdout}"
        )

    def test_commit_msg_hook_rejects_invalid_format(self, commit_msg_script, tmp_path):
        """Verify hook rejects non-conventional commit messages."""
        if not commit_msg_script.exists():
            pytest.skip("commit_msg.py script not found")

        # Create temporary commit message file with invalid format
        msg_file = tmp_path / "commit-msg.txt"
        msg_file.write_text("fixed the login bug")

        # Run hook with invalid message
        result = subprocess.run(
            [sys.executable, str(commit_msg_script), str(msg_file)],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )

        assert result.returncode != EXIT_SUCCESS, "Hook accepted invalid commit message"
        output = result.stdout + result.stderr
        assert "Conventional Commits" in output, (
            "Hook should mention Conventional Commits in error message"
        )

    def test_commit_msg_hook_accepts_scoped_commits(self, commit_msg_script, tmp_path):
        """Verify hook accepts scoped conventional commits (e.g., fix(auth): message)."""
        if not commit_msg_script.exists():
            pytest.skip("commit_msg.py script not found")

        # Test various scoped commit formats
        scoped_messages = [
            "fix(auth): resolve login timeout issue",
            "feat(ui): add new dashboard",
            "refactor(api): simplify endpoint logic",
            "test(auth): add login tests",
        ]

        for msg in scoped_messages:
            msg_file = tmp_path / f"commit-msg-{scoped_messages.index(msg)}.txt"
            msg_file.write_text(msg)

            result = subprocess.run(
                [sys.executable, str(commit_msg_script), str(msg_file)],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )

            assert result.returncode == EXIT_SUCCESS, (
                f"Hook rejected valid scoped commit: '{msg}'. "
                f"stderr: {result.stderr}, stdout: {result.stdout}"
            )

    def test_commit_msg_hook_accepts_breaking_change_commits(
        self, commit_msg_script, tmp_path
    ):
        """Verify hook accepts breaking change commits with ! syntax."""
        if not commit_msg_script.exists():
            pytest.skip("commit_msg.py script not found")

        # Test various breaking change formats
        breaking_messages = [
            "feat!: redesign API endpoints",
            "fix!: change authentication flow",
            "refactor(api)!: remove deprecated endpoints",
        ]

        for msg in breaking_messages:
            msg_file = (
                tmp_path / f"commit-msg-breaking-{breaking_messages.index(msg)}.txt"
            )
            msg_file.write_text(msg)

            result = subprocess.run(
                [sys.executable, str(commit_msg_script), str(msg_file)],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )

            assert result.returncode == EXIT_SUCCESS, (
                f"Hook rejected valid breaking change commit: '{msg}'. "
                f"stderr: {result.stderr}, stdout: {result.stdout}"
            )
