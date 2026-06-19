"""Unit tests for nwave_ai.cli._resolve_installer (uv-first migration).

Toolchain *identity* (NWAVE_INSTALLER override, uv tool dir probe, path
heuristics) is owned by the shared detector and tested in
tests/des/unit/adapters/package_managers/test_package_manager_detector.py.

These tests cover the resolver's own responsibilities:
    - mapping a detected manager to its argv prefix,
    - falling back to a uv-first PATH scan when ownership is "unknown",
    - returning None when no installer exists.

`detect_pm` is imported lazily inside `_resolve_installer`, so it is patched
at its source module (the lazy `from ... import detect_pm` re-reads it there).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from nwave_ai.cli import _resolve_installer


_DETECT_PM = "des.adapters.driven.package_managers.package_manager_detector.detect_pm"


def _which_factory(available: set[str]):
    """Return a shutil.which stand-in that reports only ``available`` tools."""

    def fake_which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in available else None

    return fake_which


# ---------------------------------------------------------------------------
# Detected owner maps to the right argv prefix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pm, expected",
    [
        ("uv", (["uv", "tool"], "uv")),
        ("pipx", (["pipx"], "pipx")),
        ("pip", (["pip"], "pip")),
    ],
)
def test_detected_owner_maps_to_command(
    pm: str, expected: tuple[list[str], str]
) -> None:
    with (
        patch(_DETECT_PM, return_value=pm),
        patch("shutil.which", side_effect=_which_factory({"uv", "pipx", "pip"})),
    ):
        assert _resolve_installer() == expected


def test_detected_owner_honored_even_when_others_present() -> None:
    """If the detector says pipx (e.g. via NWAVE_INSTALLER or pipx venv),
    the resolver must not switch to uv just because uv is also on PATH."""
    with (
        patch(_DETECT_PM, return_value="pipx"),
        patch("shutil.which", side_effect=_which_factory({"uv", "pipx"})),
    ):
        assert _resolve_installer() == (["pipx"], "pipx")


def test_detected_owner_missing_from_path_falls_through() -> None:
    """Detector names uv, but uv isn't on PATH (stale install) -> PATH scan."""
    with (
        patch(_DETECT_PM, return_value="uv"),
        patch("shutil.which", side_effect=_which_factory({"pipx"})),
    ):
        assert _resolve_installer() == (["pipx"], "pipx")


# ---------------------------------------------------------------------------
# Unknown ownership -> uv-first PATH scan
# ---------------------------------------------------------------------------


def test_unknown_owner_prefers_uv() -> None:
    with (
        patch(_DETECT_PM, return_value="unknown"),
        patch("shutil.which", side_effect=_which_factory({"uv", "pipx", "pip"})),
    ):
        assert _resolve_installer() == (["uv", "tool"], "uv")


def test_unknown_owner_falls_back_to_pipx_then_pip() -> None:
    with (
        patch(_DETECT_PM, return_value="unknown"),
        patch("shutil.which", side_effect=_which_factory({"pipx", "pip"})),
    ):
        assert _resolve_installer() == (["pipx"], "pipx")

    with (
        patch(_DETECT_PM, return_value="unknown"),
        patch("shutil.which", side_effect=_which_factory({"pip"})),
    ):
        assert _resolve_installer() == (["pip"], "pip")


def test_returns_none_when_no_installer_available() -> None:
    with (
        patch(_DETECT_PM, return_value="unknown"),
        patch("shutil.which", side_effect=_which_factory(set())),
    ):
        assert _resolve_installer() is None
