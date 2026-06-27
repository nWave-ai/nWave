"""Sandbox fixtures for the E7 install-registration slice.

Redirects `Path.home()` and `$HOME` to a per-test `tmp_path` so the real
`AttributionPlugin` and the real `attribution on|off` CLI resolve a sandboxed
`~/.claude` and `~/.nwave` — NEVER the operator's real home. Precedent:
`tests/des/unit/install/test_install_des_hooks.py` (`monkeypatch.setattr(Path,
"home", ...)`) + `tests/installer/acceptance/*/conftest.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sandbox_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A sandboxed nWave home; `Path.home()` and `$HOME` both point here.

    The `install`/`cli` composition fixtures (in the step binder) consume this so
    the real `AttributionPlugin` and `attribution on|off` CLI resolve a sandboxed
    `~/.claude` + `~/.nwave`, NEVER the operator's real home.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


@pytest.fixture
def box() -> dict[str, object]:
    """Carrier for the captured result(s) across When/Then steps."""
    return {}
