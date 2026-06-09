"""CommitVerifier - driven port for verifying git commits exist for steps.

Abstract interface defining how the application layer verifies that a real
git commit exists with a Step-ID trailer for a completed step.

Defined by: Application layer commit verification needs (fraud prevention).
Implemented by: GitCommitVerifier (infrastructure adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CommitVerificationResult:
    """Result of a commit verification check.

    Attributes:
        verified: True if a commit with the matching Step-ID trailer was found
        commit_hash: Full commit hash if found, None otherwise
        commit_date: Commit date string if found, None otherwise
        commit_subject: Commit subject line if found, None otherwise
        error_reason: Human-readable reason if verification failed
    """

    verified: bool
    commit_hash: str | None = None
    commit_date: str | None = None
    commit_subject: str | None = None
    error_reason: str | None = None


class CommitVerifier(ABC):
    """Driven port: verifies git commits exist for completed steps.

    The application layer defines WHAT constitutes a valid commit (Step-ID trailer).
    The adapter decides HOW to search for commits (git log, API, etc.).
    """

    @abstractmethod
    def verify_commit(
        self,
        step_id: str,
        cwd: str,
        feature_id_filter: str | None = None,
    ) -> CommitVerificationResult:
        """Verify a git commit exists with Step-Id trailer for the given step.

        When ``feature_id_filter`` is provided, the verifier MUST require BOTH
        a ``Step-Id: {step_id}`` trailer AND a ``Task-Id: {feature_id_filter}``
        trailer on the same commit (AND-semantics). This prevents cross-feature
        commit confusion: a step with ``Step-Id: 01-02`` in feature A being
        wrongly satisfied by a commit from feature B carrying the same step
        number. When ``feature_id_filter`` is ``None``, behaviour is unchanged
        (single-trailer ``Step-Id`` match).

        Args:
            step_id: Step identifier to search for (e.g., "01-01")
            cwd: Working directory to run git commands in
            feature_id_filter: Optional feature/task identifier. When provided,
                the commit must ALSO carry a matching ``Task-Id:`` trailer.

        Returns:
            CommitVerificationResult with verification details
        """
        ...
