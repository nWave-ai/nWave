"""Unit tests for Session Guard Policy.

Tests that source file writes during deliver sessions are blocked
unless a DES-monitored subagent is currently running.
"""

import pytest

from des.domain.session_guard_policy import SessionGuardPolicy


class TestSessionGuardPolicy:
    """Unit tests for SessionGuardPolicy."""

    @pytest.fixture
    def policy(self):
        return SessionGuardPolicy()

    def test_no_deliver_session_allows_all(self, policy):
        """Without active deliver session, all writes should be allowed."""
        result = policy.check(
            file_path="src/auth/user_auth.py",
            session_active=False,
            des_task_active=False,
        )
        assert result.blocked is False

    def test_source_write_blocked_during_deliver(self, policy):
        """Source file write during deliver without DES task should be blocked."""
        result = policy.check(
            file_path="src/auth/user_auth.py",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is True
        assert "blocked" in (result.reason or "").lower()

    def test_source_write_allowed_with_des_task(self, policy):
        """Source file write during deliver WITH DES task should be allowed."""
        result = policy.check(
            file_path="src/auth/user_auth.py",
            session_active=True,
            des_task_active=True,
        )
        assert result.blocked is False

    def test_test_write_blocked_during_deliver(self, policy):
        """Test file write during deliver without DES task should be blocked."""
        result = policy.check(
            file_path="tests/auth/test_user_auth.py",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is True

    def test_orchestration_file_allowed(self, policy):
        """Orchestration artifacts (docs/feature/) should always be allowed."""
        result = policy.check(
            file_path="docs/feature/auth-upgrade/roadmap.yaml",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is False

    def test_nwave_state_file_allowed(self, policy):
        """.nwave/ state files should always be allowed."""
        result = policy.check(
            file_path=".nwave/des/deliver-session.json",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is False

    def test_develop_progress_file_allowed(self, policy):
        """.develop-progress file should always be allowed."""
        result = policy.check(
            file_path=".develop-progress.json",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is False

    def test_unprotected_file_allowed(self, policy):
        """Files outside protected paths should be allowed even during deliver."""
        result = policy.check(
            file_path="README.md",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is False

    def test_blocked_reason_mentions_deliver(self, policy):
        """Block reason should explain it's during a deliver session."""
        result = policy.check(
            file_path="src/feature.py",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is True
        assert "deliver" in (result.reason or "").lower()

    def test_execution_log_allowed(self, policy):
        """execution-log.yaml in docs/feature/ should be allowed."""
        result = policy.check(
            file_path="docs/feature/auth-upgrade/execution-log.yaml",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked is False
