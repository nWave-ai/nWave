"""GitScopeChecker - driven adapter for checking file modification scope.

Implements the ScopeChecker port by using git diff to detect modified files
and comparing them against allowed glob patterns.

Infrastructure details (git subprocess, fnmatch matching) are hidden behind
the port interface. The application layer only sees ScopeCheckResult.
"""

from __future__ import annotations

import logging
import subprocess
from fnmatch import fnmatch
from typing import TYPE_CHECKING

from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult


if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class GitScopeChecker(ScopeChecker):
    """Checks file modification scope using git diff.

    Runs ``git diff --name-only HEAD`` in the project root directory
    and compares modified files against allowed glob patterns.
    """

    GIT_TIMEOUT_SECONDS = 5

    def check_scope(
        self,
        project_root: Path,
        allowed_patterns: list[str],
    ) -> ScopeCheckResult:
        """Check if file modifications are within allowed scope.

        Args:
            project_root: Root directory of the project (used as cwd for git)
            allowed_patterns: Glob patterns for files allowed to be modified

        Returns:
            ScopeCheckResult with violation details, or skipped=True on git failure
        """
        modified_files, error_reason = self._get_modified_files(project_root)

        if modified_files is None:
            return ScopeCheckResult(
                has_violations=False,
                skipped=True,
                skip_reason=error_reason,
            )

        out_of_scope = [
            f
            for f in modified_files
            if f.strip() and not self._matches_any_pattern(f, allowed_patterns)
        ]

        return ScopeCheckResult(
            has_violations=len(out_of_scope) > 0,
            out_of_scope_files=out_of_scope,
        )

    def _get_modified_files(self, project_root: Path) -> tuple[list[str] | None, str]:
        """Run git diff to detect modified files.

        Args:
            project_root: Directory to run git command in

        Returns:
            Tuple of (file list, error reason). File list is None on failure.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                timeout=self.GIT_TIMEOUT_SECONDS,
                check=True,
                text=True,
                cwd=str(project_root),
            )
            files = [f for f in result.stdout.strip().split("\n") if f.strip()]
            return (files, "")

        except subprocess.TimeoutExpired:
            logger.error(
                "Git diff timed out after %d seconds", self.GIT_TIMEOUT_SECONDS
            )
            return (None, "Git command timeout")

        except subprocess.CalledProcessError as e:
            logger.error("Git diff failed: %s", e)
            return (None, "Git command unavailable in environment")

        except FileNotFoundError:
            logger.error("Git executable not found")
            return (None, "Git executable not found")

    @staticmethod
    def _matches_any_pattern(file_path: str, patterns: list[str]) -> bool:
        """Check if a file path matches any of the allowed glob patterns."""
        return any(fnmatch(file_path, pattern) for pattern in patterns)
