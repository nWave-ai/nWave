"""ScopeChecker - driven port for checking file modification scope.

Abstract interface defining how the application layer checks whether
file modifications stay within allowed scope.

Defined by: Application layer scope enforcement needs.
Implemented by: GitScopeChecker (infrastructure adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ScopeCheckResult:
    """Result of a scope check.

    Attributes:
        has_violations: True if out-of-scope modifications detected
        out_of_scope_files: List of files modified outside allowed scope
        skipped: True if the check could not be performed
        skip_reason: Reason the check was skipped (None if not skipped)
    """

    has_violations: bool = False
    out_of_scope_files: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None


class ScopeChecker(ABC):
    """Driven port: checks whether file modifications stay within allowed scope.

    The application layer defines WHAT constitutes scope violations.
    The adapter decides HOW to detect modified files (git diff, filesystem, etc.).
    """

    @abstractmethod
    def check_scope(
        self,
        project_root: Path,
        allowed_patterns: list[str],
    ) -> ScopeCheckResult:
        """Check if file modifications are within allowed scope.

        Args:
            project_root: Root directory of the project
            allowed_patterns: Glob patterns for files allowed to be modified

        Returns:
            ScopeCheckResult with violation details
        """
        ...
