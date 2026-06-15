"""Unit tests for DESConfig.installed_package_manager.

The PM that installed nwave-ai is recorded in the GLOBAL config under
``install.package_manager`` and consumed by /nw-update. It is machine-scoped
(one nwave-ai package per machine), like update_check state.
"""

import json

from des.adapters.driven.config.des_config import DESConfig


def _config(tmp_path, global_content: dict | None) -> DESConfig:
    global_path = tmp_path / "global-config.json"
    if global_content is not None:
        global_path.write_text(json.dumps(global_content), encoding="utf-8")
    project_path = tmp_path / ".nwave" / "des-config.json"
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text("{}", encoding="utf-8")
    return DESConfig(config_path=project_path, global_config_path=global_path)


def test_returns_recorded_package_manager(tmp_path) -> None:
    config = _config(tmp_path, {"install": {"package_manager": "uv"}})

    assert config.installed_package_manager == "uv"


def test_returns_none_when_install_block_absent(tmp_path) -> None:
    config = _config(tmp_path, {"rigor": {"profile": "standard"}})

    assert config.installed_package_manager is None


def test_returns_none_when_global_config_missing(tmp_path) -> None:
    config = _config(tmp_path, None)

    assert config.installed_package_manager is None


def test_ignores_project_local_install_block(tmp_path) -> None:
    """Recording is machine-global; a project-local install block must not leak."""
    global_path = tmp_path / "global-config.json"
    global_path.write_text("{}", encoding="utf-8")
    project_path = tmp_path / ".nwave" / "des-config.json"
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text(
        json.dumps({"install": {"package_manager": "pipx"}}), encoding="utf-8"
    )

    config = DESConfig(config_path=project_path, global_config_path=global_path)

    assert config.installed_package_manager is None
