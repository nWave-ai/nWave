"""Focused regression tests for GitCommitVerifier process failures."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from des.adapters.driven.git.git_commit_verifier import GitCommitVerifier


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        (FileNotFoundError(), "git executable not found on PATH"),
        (
            subprocess.TimeoutExpired(cmd=["git", "log"], timeout=5),
            "git log timed out after 5s",
        ),
        (PermissionError("permission denied"), "could not run git: permission denied"),
        (RuntimeError("surprise"), "Unexpected git verification error: surprise"),
    ],
)
def test_process_failures_have_actionable_distinct_reasons(
    failure: Exception,
    expected_reason: str,
) -> None:
    with patch(
        "des.adapters.driven.git.git_commit_verifier.subprocess.run",
        side_effect=failure,
    ):
        result = GitCommitVerifier().verify_commit("01-01", "/repo")

    assert result.verified is False
    assert result.error_reason == expected_reason
