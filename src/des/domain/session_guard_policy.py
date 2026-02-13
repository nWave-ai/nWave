"""Session Guard Policy - blocks source writes during deliver without DES.

Pure domain policy that prevents the main agent from writing to source/test
files during a deliver session unless a DES-monitored subagent is currently
running. Orchestration artifacts (docs/feature/, .nwave/, .develop-progress)
are always allowed.

This closes Scenario B: the main agent implementing steps directly with
Read/Write/Edit instead of delegating to a software-crafter via Task.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardResult:
    """Result of a session guard check.

    Attributes:
        blocked: True if the write should be blocked
        reason: Block reason if blocked, None otherwise
    """

    blocked: bool
    reason: str | None = None


class SessionGuardPolicy:
    """Guards source file writes during deliver sessions.

    Protected paths: src/, tests/ (must go through DES subagent)
    Allowed paths: docs/feature/, .nwave/, .develop-progress (orchestration)
    """

    PROTECTED_PATTERNS = ["src/", "tests/"]

    ALLOWED_PATTERNS = [
        "docs/feature/",
        ".nwave/",
        ".develop-progress",
    ]

    def check(
        self,
        file_path: str,
        session_active: bool,
        des_task_active: bool,
    ) -> GuardResult:
        """Check if a file write should be allowed.

        Args:
            file_path: Path of the file being written
            session_active: True if a deliver session is active
            des_task_active: True if a DES-monitored subagent is running
        """
        if not session_active:
            return GuardResult(blocked=False)

        if any(p in file_path for p in self.ALLOWED_PATTERNS):
            return GuardResult(blocked=False)

        if not any(p in file_path for p in self.PROTECTED_PATTERNS):
            return GuardResult(blocked=False)

        if des_task_active:
            return GuardResult(blocked=False)

        return GuardResult(
            blocked=True,
            reason=(
                "Source write blocked during deliver session. "
                "Source/test files must be written by a DES-monitored "
                "software-crafter subagent, not directly by the orchestrator. "
                "Delegate this work via Task with DES markers."
            ),
        )
