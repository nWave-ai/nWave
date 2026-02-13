"""GitCommitVerifier - git-based adapter for commit verification.

Uses subprocess to call git log and search for commits containing
a Step-ID trailer in the commit message body.

Implements: CommitVerifier driven port.
"""

from __future__ import annotations

import subprocess

from des.ports.driven_ports.commit_verifier import (
    CommitVerificationResult,
    CommitVerifier,
)


class GitCommitVerifier(CommitVerifier):
    """Verifies git commits exist with Step-ID trailers using git CLI.

    Searches the full commit message (subject + body) for the trailer
    pattern "Step-ID: {step_id}" using git log --grep.
    """

    def verify_commit(self, step_id: str, cwd: str) -> CommitVerificationResult:
        """Verify a git commit exists with Step-ID trailer for the given step.

        Uses git log --grep to search commit messages for the Step-ID trailer.
        Searches the full message (subject + body), not just the subject line.

        Args:
            step_id: Step identifier to search for (e.g., "01-01")
            cwd: Working directory to run git commands in

        Returns:
            CommitVerificationResult with verification details
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--format=%H|%ai|%s",
                    f"--grep=Step-ID: {step_id}",
                    "-1",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=cwd,
            )

            if result.returncode != 0:
                return CommitVerificationResult(
                    verified=False,
                    error_reason=f"git command failed: {result.stderr.strip()}",
                )

            output = result.stdout.strip()
            if not output:
                return CommitVerificationResult(
                    verified=False,
                    error_reason=f"No commit found with Step-ID: {step_id}",
                )

            parts = output.split("|", 2)
            return CommitVerificationResult(
                verified=True,
                commit_hash=parts[0] if len(parts) > 0 else None,
                commit_date=parts[1] if len(parts) > 1 else None,
                commit_subject=parts[2] if len(parts) > 2 else None,
            )

        except Exception as e:
            return CommitVerificationResult(
                verified=False,
                error_reason=f"Git verification error: {e}",
            )
