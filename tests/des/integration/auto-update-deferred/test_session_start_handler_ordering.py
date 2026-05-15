"""Integration tests for session_start_handler early-phase pending-update apply.

Verifies that when a pending-update flag is present, the handler:
1. Invokes PendingUpdateService.apply() BEFORE housekeeping/update_check.
2. Selects the adapter implementation based on flag.pm (pipx -> PipxAdapter,
   uv -> UvAdapter, unknown -> service handles internally without adapter).
3. Is a no-op for the apply block when the flag is absent (session proceeds).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


def _write_flag(home: Path, pm: str, binary: str = "/usr/bin/pipx") -> None:
    nwave_dir = home / ".nwave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    (nwave_dir / "pending-update.json").write_text(
        json.dumps(
            {
                "pm": pm,
                "pm_binary_abspath": binary,
                "target_version": "2.0.0",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "attempt_count": 0,
                "last_error": None,
            }
        ),
        encoding="utf-8",
    )


def _invoke_with_call_recorder(tmp_path, calls: list[str]):
    """Invoke handle_session_start capturing call order in ``calls``."""
    from des.adapters.drivers.hooks import session_start_handler as mod

    mock_stdin = MagicMock()
    mock_stdin.read.return_value = "{}"
    captured = StringIO()

    # Spy PendingUpdateService.apply
    spy_service = MagicMock()
    spy_service.apply = MagicMock(
        side_effect=lambda: calls.append("apply") or _noop_result()
    )

    # Build spy to replace PendingUpdateService constructor
    ctor_spy = MagicMock(return_value=spy_service)

    def _hk(*_a, **_kw):
        calls.append("housekeeping")

    def _uc(*_a, **_kw):
        calls.append("update_check")
        svc = MagicMock()
        result = MagicMock()
        result.status = "UP_TO_DATE"
        svc.check_for_updates.return_value = result
        return svc

    with (
        patch("sys.stdin", mock_stdin),
        patch("sys.stdout", captured),
        patch.object(mod, "_run_housekeeping", side_effect=_hk),
        patch.object(mod, "_build_update_check_service", side_effect=_uc),
        patch(
            "des.application.pending_update_service.PendingUpdateService",
            ctor_spy,
        ),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        exit_code = mod.handle_session_start()

    return exit_code, ctor_spy, spy_service


def _noop_result():
    from des.ports.driven_ports.package_manager_port import UpgradeResult

    return UpgradeResult(success=True, error=None)


class TestSessionStartHandlerOrdering:
    def test_apply_called_before_housekeeping_and_update_check(self, tmp_path):
        _write_flag(tmp_path, pm="pipx")
        calls: list[str] = []

        exit_code, _ctor_spy, spy_service = _invoke_with_call_recorder(tmp_path, calls)

        assert exit_code == 0
        assert spy_service.apply.called, "PendingUpdateService.apply() must be invoked"
        # Ordering: apply MUST precede housekeeping and update_check
        assert calls.index("apply") < calls.index("housekeeping")
        assert calls.index("apply") < calls.index("update_check")

    def test_pipx_flag_selects_pipx_adapter(self, tmp_path):
        from des.adapters.driven.package_managers.pipx_package_manager_adapter import (
            PipxPackageManagerAdapter,
        )

        _write_flag(tmp_path, pm="pipx")
        calls: list[str] = []

        _exit, ctor_spy, _svc = _invoke_with_call_recorder(tmp_path, calls)

        assert ctor_spy.called, "PendingUpdateService should be constructed"
        # Inspect kwargs/positional: adapter is passed as `pm=`
        _args, kwargs = ctor_spy.call_args
        adapter = kwargs.get("pm") or (_args[1] if len(_args) > 1 else None)
        assert isinstance(adapter, PipxPackageManagerAdapter)

    def test_uv_flag_selects_uv_adapter(self, tmp_path):
        from des.adapters.driven.package_managers.uv_package_manager_adapter import (
            UvPackageManagerAdapter,
        )

        _write_flag(tmp_path, pm="uv", binary="/usr/bin/uv")
        calls: list[str] = []

        _exit, ctor_spy, _svc = _invoke_with_call_recorder(tmp_path, calls)

        _args, kwargs = ctor_spy.call_args
        adapter = kwargs.get("pm") or (_args[1] if len(_args) > 1 else None)
        assert isinstance(adapter, UvPackageManagerAdapter)

    def test_absent_flag_is_noop_for_apply_block(self, tmp_path):
        # No flag written. Handler must still run housekeeping + update_check.
        calls: list[str] = []

        exit_code, _ctor_spy, _spy = _invoke_with_call_recorder(tmp_path, calls)

        assert exit_code == 0
        # Either the service isn't constructed, or apply() is a no-op returning
        # success when read_pending_update() returns None. We assert by behavior:
        # the session proceeds (housekeeping + update_check run).
        assert "housekeeping" in calls
        assert "update_check" in calls
