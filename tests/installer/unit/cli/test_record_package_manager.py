"""Unit tests for recording the package manager at install time.

`nwave-ai install` records the detected PM into the global config so that
`/nw-update` can read a trustworthy value later (its own ambient interpreter
is the wrong anchor). Detection runs here under the nwave-ai process, where
sys.executable is the install interpreter.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from nwave_ai import cli


_DETECT_PM = "des.adapters.driven.package_managers.package_manager_detector.detect_pm"


def _read_global(config_dir):
    return json.loads((config_dir / "global-config.json").read_text(encoding="utf-8"))


def test_records_detected_pm_into_global_config(tmp_path) -> None:
    with patch(_DETECT_PM, return_value="uv"):
        cli._record_package_manager(tmp_path)

    assert _read_global(tmp_path)["install"]["package_manager"] == "uv"


def test_preserves_unrelated_global_config_keys(tmp_path) -> None:
    (tmp_path / "global-config.json").write_text(
        json.dumps({"rigor": {"profile": "standard"}}), encoding="utf-8"
    )

    with patch(_DETECT_PM, return_value="pipx"):
        cli._record_package_manager(tmp_path)

    saved = _read_global(tmp_path)
    assert saved["rigor"]["profile"] == "standard"
    assert saved["install"]["package_manager"] == "pipx"


def test_never_raises_when_detection_fails(tmp_path) -> None:
    # A detection error must not break the install.
    with patch(_DETECT_PM, side_effect=RuntimeError("boom")):
        cli._record_package_manager(tmp_path)  # must not raise

    # Nothing written, no crash.
    assert not (tmp_path / "global-config.json").exists()
