"""Unit tests for the pre-fix simulator (bug #48 faithful mirror)."""

from __future__ import annotations

from tests.state_delta.fixtures.simulators_pre_fix import (
    SYSTEM_PATH_FALLBACK,
    update_path_in_settings_pre_fix,
)


def test_pre_fix_simulator_drops_user_dirs() -> None:
    """Pre-fix logic ignores existing_path: user dirs must be absent from result."""
    result = update_path_in_settings_pre_fix(
        existing_path="/home/u/.local/bin:/usr/bin",
        des_bin="/des/bin",
    )
    assert "/home/u/.local/bin" not in result


def test_pre_fix_simulator_returns_des_bin_prefixed_fallback() -> None:
    """Pre-fix result is exactly des_bin + ':' + SYSTEM_PATH_FALLBACK."""
    des_bin = "/some/des/bin"
    result = update_path_in_settings_pre_fix(
        existing_path="/home/user/.cargo/bin:/usr/bin",
        des_bin=des_bin,
    )
    assert result == f"{des_bin}:{SYSTEM_PATH_FALLBACK}"
