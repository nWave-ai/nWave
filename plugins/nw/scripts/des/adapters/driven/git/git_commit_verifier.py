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
    """Verifies git commits exist with Step-Id trailers using git CLI.

    Searches the full commit message (subject + body) for the trailer
    pattern "Step-Id: {step_id}" using ``git log --grep``. When a
    ``feature_id_filter`` is supplied, also requires a matching
    ``Task-Id: {feature_id_filter}`` trailer on the same commit
    (``--all-match`` AND-semantics).
    """

    def verify_commit(
        self,
        step_id: str,
        cwd: str,
        feature_id_filter: str | None = None,
    ) -> CommitVerificationResult:
        """Verify a git commit exists with Step-Id trailer for the given step.

        Uses ``git log --grep`` to search commit messages for the Step-Id
        trailer. Searches the full message (subject + body), not just the
        subject line. When ``feature_id_filter`` is supplied, runs a dual-grep
        with ``--all-match`` so BOTH ``Step-Id: {step_id}`` AND
        ``Task-Id: {feature_id_filter}`` must appear on the same commit.

        Args:
            step_id: Step identifier to search for (e.g., "01-01")
            cwd: Working directory to run git commands in
            feature_id_filter: Optional feature/task identifier. When provided,
                the commit must ALSO carry a matching ``Task-Id:`` trailer.

        Returns:
            CommitVerificationResult with verification details
        """
        try:
            cmd: list[str] = [
                "git",
                "log",
                "--format=%H|%ai|%s",
                f"--grep=Step-Id: {step_id}",
            ]
            if feature_id_filter is not None:
                cmd.extend(
                    [
                        "--all-match",
                        f"--grep=Task-Id: {feature_id_filter}",
                    ]
                )
            cmd.append("-1")

            result = subprocess.run(
                cmd,
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
                missing = f"Step-Id: {step_id}"
                if feature_id_filter is not None:
                    missing += f" AND Task-Id: {feature_id_filter}"
                return CommitVerificationResult(
                    verified=False,
                    error_reason=f"No commit found with {missing}",
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
