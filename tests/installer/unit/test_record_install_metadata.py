"""Unit tests for install-metadata recording.

``record_install_metadata`` writes the install provenance into the GLOBAL config
(``~/.nwave/global-config.json``):
  - ``install.installed_version`` — the package version that deployed the
    framework, the anchor the doctor VersionSyncCheck compares against the live
    ``importlib.metadata`` version to detect "upgraded but not reinstalled" drift.
  - ``install.package_manager`` — consumed by ``/nw-update`` (closes the
    previously-empty ``installed_package_manager`` gap).

Contract: read-modify-write (never clobbers unrelated keys) and best-effort
(never raises — an install must not fail because a metadata write failed).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from scripts.install import install_nwave
from scripts.install.install_nwave import (
    _detect_package_manager,
    record_install_metadata,
)


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("executable", "expected"),
    [
        ("/home/u/.local/share/pipx/venvs/nwave-ai/bin/python", "pipx"),
        ("/home/u/.local/share/uv/tools/nwave-ai/bin/python", "uv"),
        ("/home/u/.venv/bin/python", None),
        ("/usr/bin/python3", None),
        ("", None),
    ],
)
def test_detect_package_manager_from_interpreter_path(
    executable: str, expected: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PM is inferred from the tool-venv marker in the interpreter path.

    Drives ``install.package_manager`` (consumed by ``/nw-update``); a misread
    here silently corrupts that downstream workflow, so each marker branch and
    the no-match / empty-path fallbacks are pinned.
    """
    monkeypatch.setattr(install_nwave.sys, "executable", executable)
    assert _detect_package_manager() == expected


def test_writes_installed_version_and_package_manager(tmp_path: Path) -> None:
    cfg = tmp_path / ".nwave" / "global-config.json"

    record_install_metadata(cfg, installed_version="1.2.0", package_manager="pipx")

    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["install"]["installed_version"] == "1.2.0"
    assert data["install"]["package_manager"] == "pipx"


def test_creates_parent_directory_when_absent(tmp_path: Path) -> None:
    cfg = tmp_path / "nested" / ".nwave" / "global-config.json"

    record_install_metadata(cfg, installed_version="2.0.0", package_manager=None)

    assert cfg.exists()
    assert (
        json.loads(cfg.read_text(encoding="utf-8"))["install"]["installed_version"]
        == "2.0.0"
    )


def test_preserves_unrelated_existing_keys(tmp_path: Path) -> None:
    cfg = tmp_path / ".nwave" / "global-config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps(
            {
                "rigor": {"profile": "thorough"},
                "update_check": {"frequency": "weekly"},
                "install": {"package_manager": "uv"},
            }
        ),
        encoding="utf-8",
    )

    record_install_metadata(cfg, installed_version="3.0.0", package_manager="uv")

    data = json.loads(cfg.read_text(encoding="utf-8"))
    # Unrelated blocks untouched.
    assert data["rigor"] == {"profile": "thorough"}
    assert data["update_check"] == {"frequency": "weekly"}
    # install block updated, sibling install keys preserved.
    assert data["install"]["installed_version"] == "3.0.0"
    assert data["install"]["package_manager"] == "uv"


def test_omits_package_manager_when_none(tmp_path: Path) -> None:
    cfg = tmp_path / ".nwave" / "global-config.json"

    record_install_metadata(cfg, installed_version="1.0.0", package_manager=None)

    install_block = json.loads(cfg.read_text(encoding="utf-8"))["install"]
    assert install_block["installed_version"] == "1.0.0"
    assert "package_manager" not in install_block


def test_does_not_drop_existing_package_manager_when_none(tmp_path: Path) -> None:
    """A None PM on a re-record must not erase a previously recorded PM."""
    cfg = tmp_path / ".nwave" / "global-config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"install": {"package_manager": "pipx"}}), encoding="utf-8"
    )

    record_install_metadata(cfg, installed_version="1.1.0", package_manager=None)

    install_block = json.loads(cfg.read_text(encoding="utf-8"))["install"]
    assert install_block["installed_version"] == "1.1.0"
    assert install_block["package_manager"] == "pipx"


def test_best_effort_on_corrupt_existing_config(tmp_path: Path) -> None:
    """Corrupt existing JSON is overwritten with a fresh valid config, no raise."""
    cfg = tmp_path / ".nwave" / "global-config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{ not json", encoding="utf-8")

    record_install_metadata(cfg, installed_version="1.0.0", package_manager="uv")

    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["install"]["installed_version"] == "1.0.0"
