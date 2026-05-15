"""Integration tests for the session-start handler full flow.

Covers the complete session-start path:
  DESConfig (reads frequency) -> UpdateCheckPolicy (gates) ->
  UpdateCheckService (PyPI + GitHub) -> session_start_handler (stdout JSON)

Tests validate all AC scenarios:
1. UPDATE_AVAILABLE produces additionalContext JSON on stdout
2. UP_TO_DATE produces no stdout and exit 0
3. PyPI timeout produces no stdout and exit 0
4. GitHub API failure produces additionalContext with version only (no changelog)
5. frequency=never produces no stdout without any network calls

Each test uses:
  - Real DESConfig wired to a tmp_path config file (no mocks inside hexagon)
  - Stubbed PyPI and GitHub HTTP endpoints via unittest.mock.patch on urllib
  - Captured stdout via io.StringIO patched into sys.stdout
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pypi_response(version: str) -> bytes:
    """Build a minimal valid PyPI JSON response body for nwave-ai."""
    payload = {"info": {"version": version}}
    return json.dumps(payload).encode()


def _make_github_response(version: str, body: str | None) -> bytes:
    """Build a minimal valid GitHub releases API response body."""
    payload = {"tag_name": f"v{version}", "body": body}
    return json.dumps(payload).encode()


def _make_mock_response(data: bytes, status: int = 200):
    """Build a mock urllib response object (context-manager compatible)."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = data
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _write_config(config_file: Path, data: dict) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _invoke_handler(
    config_file: Path,
    local_version: str = "1.0.0",
    urlopen_side_effect=None,
    urlopen_return_value=None,
) -> tuple[int, str]:
    """Invoke handle_session_start with injected config and captured stdout.

    Patches:
    - urllib.request.urlopen: controlled HTTP responses
    - _build_update_check_service: injects DESConfig with test config_path
    - _get_local_version: returns the given local_version
    - sys.stdin: avoids blocking on stdin.read()
    - sys.stdout: captured via StringIO

    Returns:
        (exit_code, captured_stdout_text)
    """
    from des.adapters.driven.config.des_config import DESConfig
    from des.adapters.drivers.hooks.session_start_handler import handle_session_start
    from des.application.update_check_service import UpdateCheckService

    captured = StringIO()
    mock_stdin = MagicMock()
    mock_stdin.read.return_value = "{}"

    def _build_service_for_test(_des_config=None):
        des_config = DESConfig(config_path=config_file)
        return UpdateCheckService(
            des_config=des_config,
            local_version=local_version,
        )

    urlopen_kwargs: dict = {}
    if urlopen_side_effect is not None:
        urlopen_kwargs["side_effect"] = urlopen_side_effect
    elif urlopen_return_value is not None:
        urlopen_kwargs["return_value"] = urlopen_return_value

    with (
        patch("sys.stdin", mock_stdin),
        patch("sys.stdout", captured),
        patch(
            "des.adapters.drivers.hooks.session_start_handler._build_update_check_service",
            side_effect=_build_service_for_test,
        ),
        patch(
            "des.adapters.drivers.hooks.session_start_handler._get_local_version",
            return_value=local_version,
        ),
        patch("urllib.request.urlopen", **urlopen_kwargs),
    ):
        exit_code = handle_session_start()

    return exit_code, captured.getvalue()


# ---------------------------------------------------------------------------
# Integration test class
# ---------------------------------------------------------------------------


class TestSessionStartHandlerFullFlow:
    """Full integration tests for session_start_handler."""

    def test_update_available_produces_additional_context_json(self, tmp_path):
        """UPDATE_AVAILABLE flow produces valid additionalContext JSON on stdout."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        _write_config(
            config_file,
            {
                "update_check": {
                    "frequency": "every_session",
                    "skipped_versions": [],
                }
            },
        )

        pypi_resp = _make_mock_response(_make_pypi_response("2.0.0"))
        gh_resp = _make_mock_response(
            _make_github_response("2.0.0", "## What's new\n- Feature X")
        )

        exit_code, stdout = _invoke_handler(
            config_file,
            local_version="1.0.0",
            urlopen_side_effect=[pypi_resp, gh_resp],
        )

        assert exit_code == 0
        assert stdout.strip(), "Expected non-empty stdout for UPDATE_AVAILABLE"
        payload = json.loads(stdout.strip())
        assert "additionalContext" in payload
        ctx = payload["additionalContext"]
        assert "2.0.0" in ctx, "Latest version must appear in additionalContext"

    def test_update_available_includes_changelog_when_github_succeeds(self, tmp_path):
        """UPDATE_AVAILABLE with successful GitHub response includes changelog."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        _write_config(
            config_file,
            {"update_check": {"frequency": "every_session", "skipped_versions": []}},
        )

        changelog_text = "## What's new\n- Feature X added"
        pypi_resp = _make_mock_response(_make_pypi_response("2.0.0"))
        gh_resp = _make_mock_response(_make_github_response("2.0.0", changelog_text))

        exit_code, stdout = _invoke_handler(
            config_file,
            local_version="1.0.0",
            urlopen_side_effect=[pypi_resp, gh_resp],
        )

        assert exit_code == 0
        payload = json.loads(stdout.strip())
        assert changelog_text in payload["additionalContext"]

    def test_up_to_date_produces_no_stdout(self, tmp_path):
        """UP_TO_DATE flow produces no stdout and exit 0."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        _write_config(
            config_file,
            {"update_check": {"frequency": "every_session", "skipped_versions": []}},
        )

        pypi_resp = _make_mock_response(_make_pypi_response("1.0.0"))

        exit_code, stdout = _invoke_handler(
            config_file,
            local_version="1.0.0",
            urlopen_return_value=pypi_resp,
        )

        assert exit_code == 0
        assert stdout.strip() == "", (
            f"Expected empty stdout for UP_TO_DATE, got: {stdout!r}"
        )

    def test_pypi_timeout_produces_no_stdout(self, tmp_path):
        """PyPI timeout produces no stdout and exit 0."""
        import urllib.error

        config_file = tmp_path / ".nwave" / "des-config.json"
        _write_config(
            config_file,
            {"update_check": {"frequency": "every_session", "skipped_versions": []}},
        )

        exit_code, stdout = _invoke_handler(
            config_file,
            local_version="1.0.0",
            urlopen_side_effect=urllib.error.URLError("timed out"),
        )

        assert exit_code == 0
        assert stdout.strip() == "", (
            f"Expected empty stdout on PyPI timeout, got: {stdout!r}"
        )

    def test_github_api_failure_produces_additional_context_without_changelog(
        self, tmp_path
    ):
        """GitHub API failure: additionalContext present with version but no changelog body."""
        import urllib.error

        config_file = tmp_path / ".nwave" / "des-config.json"
        _write_config(
            config_file,
            {"update_check": {"frequency": "every_session", "skipped_versions": []}},
        )

        pypi_resp = _make_mock_response(_make_pypi_response("2.0.0"))
        github_error = urllib.error.URLError("connection refused")

        exit_code, stdout = _invoke_handler(
            config_file,
            local_version="1.0.0",
            urlopen_side_effect=[pypi_resp, github_error],
        )

        assert exit_code == 0
        assert stdout.strip(), (
            "Expected non-empty stdout when PyPI succeeds but GitHub fails"
        )
        payload = json.loads(stdout.strip())
        assert "additionalContext" in payload
        ctx = payload["additionalContext"]
        assert "2.0.0" in ctx, "Latest version must appear in additionalContext"
        # changelog content absent — message ends with "Changes: "
        assert "Feature" not in ctx, (
            "Changelog content should not appear when GitHub API fails"
        )

    def test_frequency_never_produces_no_stdout_without_network_calls(self, tmp_path):
        """frequency=never produces no stdout and makes no network calls."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        _write_config(
            config_file,
            {"update_check": {"frequency": "never", "skipped_versions": []}},
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            exit_code, stdout = _invoke_handler(config_file, local_version="1.0.0")
            mock_urlopen.assert_not_called()

        assert exit_code == 0
        assert stdout.strip() == "", (
            f"Expected empty stdout for frequency=never, got: {stdout!r}"
        )
