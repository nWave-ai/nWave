"""Unit tests for package_manager_detector.detect_pm.

Behaviors under test:
1. NWAVE_INSTALLER override (uv/pipx/pip) wins over auto-detection.
2. pipx path detection (substring match)
3. uv path detection (under `uv tool dir`) + `/uv/tools/` substring fallback
4. unknown path fallback
   Plus tolerance: `uv` missing / `uv tool dir` failing degrades to fallback.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from des.adapters.driven.package_managers.package_manager_detector import (
    detect_pm,
    resolve_nwave_pm,
)


_PROBE = (
    "des.adapters.driven.package_managers.package_manager_detector."
    "subprocess.check_output"
)


@pytest.fixture(autouse=True)
def _clear_installer_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep detection hermetic: drop any NWAVE_INSTALLER from the real env.

    Override tests re-set it explicitly via patch.dict.
    """
    monkeypatch.delenv("NWAVE_INSTALLER", raising=False)


class TestDetectPm:
    def test_detects_pipx_when_path_contains_pipx_venvs(self) -> None:
        executable = Path("/home/user/.local/share/pipx/venvs/nwave-ai/bin/python")
        with patch(
            "des.adapters.driven.package_managers.package_manager_detector."
            "subprocess.check_output",
            return_value="/home/user/.local/share/uv/tools\n",
        ):
            assert detect_pm(executable) == "pipx"

    def test_detects_uv_when_executable_under_uv_tool_dir(self) -> None:
        uv_tool_dir = "/home/user/.local/share/uv/tools"
        executable = Path(f"{uv_tool_dir}/nwave-ai/bin/python")
        with patch(
            "des.adapters.driven.package_managers.package_manager_detector."
            "subprocess.check_output",
            return_value=f"{uv_tool_dir}\n",
        ):
            assert detect_pm(executable) == "uv"

    def test_returns_unknown_when_no_match(self) -> None:
        executable = Path("/usr/bin/python3")
        with patch(
            "des.adapters.driven.package_managers.package_manager_detector."
            "subprocess.check_output",
            return_value="/home/user/.local/share/uv/tools\n",
        ):
            assert detect_pm(executable) == "unknown"

    @pytest.mark.parametrize(
        "exc",
        [
            FileNotFoundError("uv not installed"),
            subprocess.CalledProcessError(1, ["uv", "tool", "dir"]),
        ],
    )
    def test_uv_probe_failure_falls_back_to_pipx_match(
        self, exc: BaseException
    ) -> None:
        executable = Path("/home/user/.local/share/pipx/venvs/nwave-ai/bin/python")
        with patch(
            "des.adapters.driven.package_managers.package_manager_detector."
            "subprocess.check_output",
            side_effect=exc,
        ):
            assert detect_pm(executable) == "pipx"

    @pytest.mark.parametrize(
        "exc",
        [
            FileNotFoundError("uv not installed"),
            subprocess.CalledProcessError(1, ["uv", "tool", "dir"]),
        ],
    )
    def test_uv_probe_failure_without_pipx_returns_unknown(
        self, exc: BaseException
    ) -> None:
        executable = Path("/usr/bin/python3")
        with patch(_PROBE, side_effect=exc):
            assert detect_pm(executable) == "unknown"

    def test_uv_substring_fallback_when_probe_unavailable(self) -> None:
        """When `uv tool dir` can't run but the executable is under /uv/tools/,
        detection still resolves to uv via the substring fallback."""
        executable = Path("/home/user/.local/share/uv/tools/nwave-ai/bin/python")
        with patch(_PROBE, side_effect=FileNotFoundError("uv not installed")):
            assert detect_pm(executable) == "uv"


class TestDetectPmOverride:
    """NWAVE_INSTALLER override is honored ahead of any auto-detection."""

    @pytest.mark.parametrize("forced", ["uv", "pipx", "pip"])
    def test_override_wins_over_path_detection(self, forced: str) -> None:
        # Executable lives under pipx, but the override forces a different PM.
        executable = Path("/home/user/.local/share/pipx/venvs/nwave-ai/bin/python")
        with (
            patch.dict("os.environ", {"NWAVE_INSTALLER": forced}, clear=False),
            patch(_PROBE, return_value="/home/user/.local/share/uv/tools\n"),
        ):
            assert detect_pm(executable) == forced

    def test_override_is_case_insensitive_and_trimmed(self) -> None:
        executable = Path("/usr/bin/python3")
        with (
            patch.dict("os.environ", {"NWAVE_INSTALLER": "  UV  "}, clear=False),
            patch(_PROBE, side_effect=FileNotFoundError()),
        ):
            assert detect_pm(executable) == "uv"

    def test_unknown_override_is_ignored(self) -> None:
        executable = Path("/usr/bin/python3")
        with (
            patch.dict("os.environ", {"NWAVE_INSTALLER": "conda"}, clear=False),
            patch(_PROBE, side_effect=FileNotFoundError()),
        ):
            assert detect_pm(executable) == "unknown"

    def test_pip_reported_only_via_override(self) -> None:
        # No path marker identifies pip, so pip surfaces only when forced.
        executable = Path("/usr/bin/python3")
        with (
            patch.dict("os.environ", {"NWAVE_INSTALLER": "pip"}, clear=False),
            patch(_PROBE, side_effect=FileNotFoundError()),
        ):
            assert detect_pm(executable) == "pip"


class TestResolveNwavePm:
    """resolve_nwave_pm: override > recorded value > path detection.

    Regression for /nw-update reporting 'unknown' under uv installs: the skill
    runs via an ambient python3 whose path has no PM marker, so detect_pm alone
    yields 'unknown'. The recorded install-time value must take precedence.
    """

    # An interpreter with NO package-manager marker (the /nw-update situation).
    _AMBIENT = Path("/home/user/.local/share/virtualenvs/dev/bin/python3")

    def test_recorded_value_used_when_path_detection_would_be_unknown(self) -> None:
        with patch(_PROBE, side_effect=FileNotFoundError()):
            assert resolve_nwave_pm("uv", self._AMBIENT) == "uv"
            assert resolve_nwave_pm("pipx", self._AMBIENT) == "pipx"

    def test_override_wins_over_recorded_value(self) -> None:
        with (
            patch.dict("os.environ", {"NWAVE_INSTALLER": "pipx"}, clear=False),
            patch(_PROBE, side_effect=FileNotFoundError()),
        ):
            assert resolve_nwave_pm("uv", self._AMBIENT) == "pipx"

    def test_falls_back_to_path_detection_when_unrecorded(self) -> None:
        uv_exe = Path("/home/user/.local/share/uv/tools/nwave-ai/bin/python")
        with patch(_PROBE, side_effect=FileNotFoundError()):
            assert resolve_nwave_pm(None, uv_exe) == "uv"

    @pytest.mark.parametrize("recorded", [None, "unknown", "conda", ""])
    def test_invalid_or_missing_recorded_falls_back(self, recorded) -> None:
        # Ambient interpreter has no marker -> unknown when recorded is unusable.
        with patch(_PROBE, side_effect=FileNotFoundError()):
            assert resolve_nwave_pm(recorded, self._AMBIENT) == "unknown"
