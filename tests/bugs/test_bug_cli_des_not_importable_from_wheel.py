"""Regression: ``nwave-ai`` CLI crashes with ``No module named 'des'``.

Reported defect (v3.21.0rc1): ``nwave-ai project enable`` exits with
``ModuleNotFoundError: No module named 'des'`` from ``cli.py`` doing a bare
``from des.application.auto_marking_service import AutoMarkingService``.

Root cause: the PUBLISHED wheel ships the ``des`` package at
``site-packages/nWave/lib/python/des/`` (a Hatch force-include destination), NOT
as a top-level ``des/`` package. Nothing put ``nWave/lib/python`` on ``sys.path``,
so every ``from des ...`` in the CLI failed at runtime. ``project`` / ``status`` /
``plugin install`` imported ``des`` unguarded → hard crash; ``install`` /
``doctor`` imported it guarded → silent degradation.

The dev tree CANNOT reproduce the raw crash (here ``des`` resolves from
``src/des``), so these tests encode the MISSING MECHANISM instead: the CLI's
ability to locate the wheel-bundled ``des`` and prepend it to ``sys.path``.
Before the fix neither ``_bundled_des_paths`` nor ``_ensure_des_importable``
exists, so the import below fails — RED for the right reason.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from nwave_ai.cli import _bundled_des_paths, _ensure_des_importable


if TYPE_CHECKING:
    import pytest


def _make_wheel_layout(tmp_path: Path) -> tuple[Path, Path]:
    """Build a fake installed wheel: ``site-packages/{nwave_ai, nWave/lib/python/des}``.

    Returns ``(pkg_dir, bundled_lib)`` where ``pkg_dir`` is the ``nwave_ai``
    package dir (the value ``Path(__file__).parent`` takes at runtime) and
    ``bundled_lib`` is the directory that must end up on ``sys.path``.
    """
    site = tmp_path / "site-packages"
    pkg_dir = site / "nwave_ai"
    pkg_dir.mkdir(parents=True)
    bundled_lib = site / "nWave" / "lib" / "python"
    (bundled_lib / "des").mkdir(parents=True)
    (bundled_lib / "des" / "__init__.py").write_text("", encoding="utf-8")
    return pkg_dir, bundled_lib


def test_bundled_des_paths_finds_wheel_bundled_location(tmp_path: Path) -> None:
    """The wheel-bundled ``nWave/lib/python`` (sibling of ``nwave_ai``) is found."""
    pkg_dir, bundled_lib = _make_wheel_layout(tmp_path)
    home = tmp_path / "home"  # no ~/.claude/lib/python/des here
    home.mkdir()

    assert _bundled_des_paths(pkg_dir, home) == [bundled_lib]


def test_bundled_des_paths_prefers_wheel_then_home_and_skips_missing(
    tmp_path: Path,
) -> None:
    """Both locations present → wheel-bundled first, then the installer copy."""
    pkg_dir, bundled_lib = _make_wheel_layout(tmp_path)
    home = tmp_path / "home"
    home_lib = home / ".claude" / "lib" / "python"
    (home_lib / "des").mkdir(parents=True)

    assert _bundled_des_paths(pkg_dir, home) == [bundled_lib, home_lib]


def test_bundled_des_paths_empty_when_nothing_bundled(tmp_path: Path) -> None:
    """No bundled ``des`` anywhere → no candidates (would degrade, not lie)."""
    pkg_dir = tmp_path / "site-packages" / "nwave_ai"
    pkg_dir.mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()

    assert _bundled_des_paths(pkg_dir, home) == []


def test_ensure_des_importable_prepends_wheel_path_when_des_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduction: with ``des`` not importable, the bundled lib is prepended.

    This is the path that was entirely absent before the fix — the bare import
    had no fallback, so the CLI crashed.
    """
    pkg_dir, bundled_lib = _make_wheel_layout(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    # Isolated sys.path copy so the real interpreter path is untouched.
    monkeypatch.setattr(sys, "path", ["<placeholder>"])

    inserted = _ensure_des_importable(pkg_dir, home, is_importable=lambda: False)

    assert inserted == bundled_lib
    assert sys.path[0] == str(bundled_lib)


def test_ensure_des_importable_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Calling twice must not stack duplicate entries on ``sys.path``."""
    pkg_dir, bundled_lib = _make_wheel_layout(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(sys, "path", ["<placeholder>"])

    _ensure_des_importable(pkg_dir, home, is_importable=lambda: False)
    _ensure_des_importable(pkg_dir, home, is_importable=lambda: False)

    assert sys.path.count(str(bundled_lib)) == 1


def test_ensure_des_importable_noop_when_already_importable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dev tree / editable install (``des`` already resolves) → sys.path untouched."""
    pkg_dir, _bundled_lib = _make_wheel_layout(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    before = ["<placeholder>"]
    monkeypatch.setattr(sys, "path", list(before))

    result = _ensure_des_importable(pkg_dir, home, is_importable=lambda: True)

    assert result is None
    assert sys.path == before
