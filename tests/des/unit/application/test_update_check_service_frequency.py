"""Unit tests for UpdateCheckService - frequency gate and state persistence.

Tests the frequency gating and state persistence behavior through the public API
(check_for_updates), verifying observable outcomes at driven port boundaries
(HTTP endpoint injection, DESConfig injection).

Test Budget: 5 behaviors x 2 = 10 max unit tests. Actual: 6 tests.

Behaviors:
1. Service exits silently without network calls when policy returns SKIP
2. Service persists last_checked=now after UP_TO_DATE result
3. Service persists last_checked=now after UPDATE_AVAILABLE result
4. Service does not persist last_checked when PyPI returns SKIP (network failure)
5. Service sets frequency=daily and proceeds with check on first run (no update_check key)
"""

from __future__ import annotations

import json
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from des.adapters.driven.config.des_config import DESConfig
from des.application.update_check_service import UpdateCheckService, UpdateStatus


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_pypi_response(version: str) -> bytes:
    payload: dict[str, Any] = {"info": {"version": version}}
    return json.dumps(payload).encode("utf-8")


class _PyPIHandler(BaseHTTPRequestHandler):
    """Simple handler returning a configurable PyPI response."""

    version: str = "1.0.0"

    def do_GET(self) -> None:
        body = make_pypi_response(self.__class__.version)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: Any) -> None:
        pass


def _start_server(
    handler_class: type[BaseHTTPRequestHandler],
) -> tuple[HTTPServer, str]:
    """Start a local HTTP server and return (server, base_url)."""
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def _make_config(tmp_path: Path, data: dict[str, Any]) -> DESConfig:
    """Return a DESConfig whose update_check state lives in the global config.

    update_check is machine-scoped, so the given data (an update_check block)
    is written to ``global-config.json``; the project config stays empty.
    """
    global_path = _global_path(tmp_path)
    global_path.write_text(json.dumps(data), encoding="utf-8")
    project_path = tmp_path / ".nwave" / "des-config.json"
    project_path.parent.mkdir(parents=True)
    project_path.write_text("{}", encoding="utf-8")
    return DESConfig(config_path=project_path, global_config_path=global_path)


def _global_path(tmp_path: Path) -> Path:
    """Path to the global config file used for update_check state in tests."""
    return tmp_path / "global-config.json"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUpdateCheckServiceFrequencyGate:
    """Tests: frequency gate prevents network calls when policy says SKIP."""

    def test_no_network_calls_when_policy_returns_skip(self) -> None:
        """Service exits silently without making any network requests when policy skips."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = _make_config(
                tmp_path,
                {"update_check": {"frequency": "never"}},
            )
            call_count = 0

            class CountingHandler(_PyPIHandler):
                def do_GET(self) -> None:
                    nonlocal call_count
                    call_count += 1
                    super().do_GET()

            server, base_url = _start_server(CountingHandler)
            try:
                service = UpdateCheckService(
                    pypi_url=f"{base_url}/pypi/nwave-ai/json",
                    local_version="1.0.0",
                    des_config=config,
                )
                result = service.check_for_updates()
                assert result.status == UpdateStatus.SKIP
                assert call_count == 0, (
                    "Expected no network calls when policy says SKIP"
                )
            finally:
                server.shutdown()

    def test_policy_receives_skipped_versions_from_config(self) -> None:
        """Policy receives skipped_versions from DESConfig when evaluating skip logic."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Configure a skipped version matching the PyPI latest
            config = _make_config(
                tmp_path,
                {
                    "update_check": {
                        "frequency": "daily",
                        "skipped_versions": ["2.0.0"],
                    }
                },
            )

            class V2Handler(_PyPIHandler):
                version = "2.0.0"

            server, base_url = _start_server(V2Handler)
            try:
                service = UpdateCheckService(
                    pypi_url=f"{base_url}/pypi/nwave-ai/json",
                    local_version="1.0.0",
                    des_config=config,
                )
                result = service.check_for_updates()
                # PyPI fetched (no last_checked → window expired), but
                # policy skips because 2.0.0 is in skipped list
                assert result.status == UpdateStatus.SKIP
            finally:
                server.shutdown()


class TestUpdateCheckServiceStatePersistence:
    """Tests: last_checked is persisted after successful PyPI fetch."""

    def test_persists_last_checked_after_up_to_date_result(self) -> None:
        """Service persists last_checked timestamp after UP_TO_DATE check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = _make_config(
                tmp_path,
                {"update_check": {"frequency": "daily"}},
            )

            class SameVersionHandler(_PyPIHandler):
                version = "1.0.0"

            server, base_url = _start_server(SameVersionHandler)
            try:
                service = UpdateCheckService(
                    pypi_url=f"{base_url}/pypi/nwave-ai/json",
                    local_version="1.0.0",
                    des_config=config,
                )
                result = service.check_for_updates()
                assert result.status == UpdateStatus.UP_TO_DATE

                saved = json.loads(_global_path(tmp_path).read_text())
                assert saved["update_check"]["last_checked"] is not None
            finally:
                server.shutdown()

    def test_persists_last_checked_after_update_available_result(self) -> None:
        """Service persists last_checked timestamp after UPDATE_AVAILABLE check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = _make_config(
                tmp_path,
                {"update_check": {"frequency": "daily"}},
            )

            class NewerVersionHandler(_PyPIHandler):
                version = "2.0.0"

            server, base_url = _start_server(NewerVersionHandler)
            try:
                service = UpdateCheckService(
                    pypi_url=f"{base_url}/pypi/nwave-ai/json",
                    local_version="1.0.0",
                    des_config=config,
                )
                result = service.check_for_updates()
                assert result.status == UpdateStatus.UPDATE_AVAILABLE

                saved = json.loads(_global_path(tmp_path).read_text())
                assert saved["update_check"]["last_checked"] is not None
                # latest discovered version is recorded for /nw-update.
                assert saved["update_check"]["latest_available"] == "2.0.0"
            finally:
                server.shutdown()

    def test_does_not_persist_last_checked_when_network_fails(self) -> None:
        """Service does not persist last_checked when PyPI call returns SKIP."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = _make_config(
                tmp_path,
                {"update_check": {"frequency": "daily"}},
            )
            service = UpdateCheckService(
                pypi_url="http://127.0.0.1:19998/pypi/nwave-ai/json",
                local_version="1.0.0",
                timeout=0.001,
                des_config=config,
            )
            result = service.check_for_updates()
            assert result.status == UpdateStatus.SKIP

            saved = json.loads(_global_path(tmp_path).read_text())
            assert saved["update_check"].get("last_checked") is None


class TestUpdateCheckServiceFirstRun:
    """Tests: first run behavior when update_check key is absent from config."""

    def test_proceeds_with_check_on_first_run_no_config(self) -> None:
        """Service sets frequency=daily and checks when update_check key is absent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Config without update_check key
            config = _make_config(tmp_path, {})

            class NewerVersionHandler(_PyPIHandler):
                version = "2.0.0"

            server, base_url = _start_server(NewerVersionHandler)
            try:
                service = UpdateCheckService(
                    pypi_url=f"{base_url}/pypi/nwave-ai/json",
                    local_version="1.0.0",
                    des_config=config,
                )
                result = service.check_for_updates()
                # First run: policy returns CHECK → service makes network call
                assert result.status == UpdateStatus.UPDATE_AVAILABLE
            finally:
                server.shutdown()
