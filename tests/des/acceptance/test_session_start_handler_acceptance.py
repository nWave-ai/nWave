"""Acceptance tests for SessionStart hook handler.

AC-03-01: Session-start hook handler writes additionalContext when UPDATE_AVAILABLE,
          produces no output when UP_TO_DATE or SKIP, and never blocks a session
          (fail-open on exceptions).
"""

import io
import json
from unittest.mock import MagicMock, patch


class TestSessionStartHandlerAcceptance:
    """Acceptance tests entered through the session_start_handler public function."""

    def test_writes_additional_context_when_update_available(self, capsys):
        """AC: Writes additionalContext JSON to stdout when UPDATE_AVAILABLE."""
        from des.adapters.drivers.hooks.session_start_handler import (
            handle_session_start,
        )
        from des.application.update_check_service import UpdateCheckResult, UpdateStatus

        update_result = UpdateCheckResult(
            status=UpdateStatus.UPDATE_AVAILABLE,
            latest="2.0.0",
            changelog="New features",
        )

        with patch(
            "des.adapters.drivers.hooks.session_start_handler._build_update_check_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.check_for_updates.return_value = update_result
            mock_factory.return_value = mock_service

            # Simulate stdin with empty JSON hook input
            with patch("sys.stdin", io.StringIO("{}")):
                exit_code = handle_session_start()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip()
        output = json.loads(captured.out.strip())
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "1.0.0" in ctx or "2.0.0" in ctx
        assert "2.0.0" in ctx
        # User-visible notice is also emitted.
        assert "2.0.0" in output["systemMessage"]

    def test_produces_no_output_when_up_to_date(self, capsys):
        """AC: Produces no stdout output and exits 0 when UP_TO_DATE."""
        from des.adapters.drivers.hooks.session_start_handler import (
            handle_session_start,
        )
        from des.application.update_check_service import UpdateCheckResult, UpdateStatus

        update_result = UpdateCheckResult(status=UpdateStatus.UP_TO_DATE)

        with patch(
            "des.adapters.drivers.hooks.session_start_handler._build_update_check_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.check_for_updates.return_value = update_result
            mock_factory.return_value = mock_service

            with patch("sys.stdin", io.StringIO("{}")):
                exit_code = handle_session_start()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_produces_no_output_when_skip(self, capsys):
        """AC: Produces no stdout output and exits 0 when service returns SKIP."""
        from des.adapters.drivers.hooks.session_start_handler import (
            handle_session_start,
        )
        from des.application.update_check_service import UpdateCheckResult, UpdateStatus

        update_result = UpdateCheckResult(status=UpdateStatus.SKIP)

        with patch(
            "des.adapters.drivers.hooks.session_start_handler._build_update_check_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.check_for_updates.return_value = update_result
            mock_factory.return_value = mock_service

            with patch("sys.stdin", io.StringIO("{}")):
                exit_code = handle_session_start()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_exits_0_on_unhandled_exception(self, capsys):
        """AC: Any unhandled exception exits 0 (fail-open: session must not be blocked)."""
        from des.adapters.drivers.hooks.session_start_handler import (
            handle_session_start,
        )

        with patch(
            "des.adapters.drivers.hooks.session_start_handler._build_update_check_service"
        ) as mock_factory:
            mock_factory.side_effect = RuntimeError("network failure")

            with patch("sys.stdin", io.StringIO("{}")):
                exit_code = handle_session_start()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_additional_context_includes_versions_and_changelog(self, capsys):
        """AC: additionalContext message includes local version, latest version, changelog."""
        from des.adapters.drivers.hooks.session_start_handler import (
            handle_session_start,
        )
        from des.application.update_check_service import UpdateCheckResult, UpdateStatus

        update_result = UpdateCheckResult(
            status=UpdateStatus.UPDATE_AVAILABLE,
            latest="3.1.0",
            changelog="- Bug fixes\n- Performance improvements",
        )

        with (
            patch(
                "des.adapters.drivers.hooks.session_start_handler._build_update_check_service"
            ) as mock_factory,
            patch(
                "des.adapters.drivers.hooks.session_start_handler._get_local_version",
                return_value="1.5.0",
            ),
        ):
            mock_service = MagicMock()
            mock_service.check_for_updates.return_value = update_result
            mock_factory.return_value = mock_service

            with patch("sys.stdin", io.StringIO("{}")):
                exit_code = handle_session_start()

        assert exit_code == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        msg = output["hookSpecificOutput"]["additionalContext"]
        assert "1.5.0" in msg  # local version
        assert "3.1.0" in msg  # latest version
        assert "Bug fixes" in msg  # changelog
