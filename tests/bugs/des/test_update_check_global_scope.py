"""Regression: update_check state must be machine-global, not per-project.

Bug
---
A fresh Claude Code session in folder B stayed silent about an available
nwave-ai update because folder A had already run the daily check that day.
Root cause: update_check cadence state (frequency, last_checked,
skipped_versions) was read from and written to the project-local
``<cwd>/.nwave/des-config.json`` instead of the machine-global
``~/.nwave/global-config.json``. Each folder therefore gated independently,
and a folder whose own config carried a same-day ``last_checked``
self-suppressed the update banner.

Fix
---
All three update_check fields are machine-scoped: reads come from the global
config, and ``save_update_check_state`` persists to the global config. The
project-local config no longer participates in update-check gating.

These tests fail on the pre-fix (project-scoped) implementation and pass once
update_check is global.
"""

import json

from des.adapters.driven.config.des_config import DESConfig


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class TestUpdateCheckIsMachineGlobal:
    """update_check state is shared across project folders via the global config."""

    def test_state_shared_across_project_folders(self, tmp_path) -> None:
        """Two project dirs sharing one global config see identical update_check state.

        This is the exact reproduction: folder A's check (recorded globally)
        must be visible to folder B so B does not redundantly re-gate.
        """
        global_config = tmp_path / "global" / "global-config.json"
        _write(
            global_config,
            {
                "update_check": {
                    "frequency": "daily",
                    "last_checked": "2026-06-15T11:39:25+00:00",
                    "skipped_versions": ["3.18.0"],
                }
            },
        )

        folder_a = tmp_path / "folderA" / ".nwave" / "des-config.json"
        folder_b = tmp_path / "folderB" / ".nwave" / "des-config.json"
        _write(folder_a, {})
        _write(folder_b, {})

        cfg_a = DESConfig(config_path=folder_a, global_config_path=global_config)
        cfg_b = DESConfig(config_path=folder_b, global_config_path=global_config)

        for cfg in (cfg_a, cfg_b):
            assert cfg.update_check_frequency == "daily"
            assert cfg.update_check_last_checked == "2026-06-15T11:39:25+00:00"
            assert cfg.update_check_skipped_versions == ["3.18.0"]

    def test_project_local_update_check_is_ignored(self, tmp_path) -> None:
        """A stale project-local update_check block must not gate the check.

        Global config has no update_check (fresh machine) -> first-run
        semantics, regardless of any per-folder update_check left behind.
        """
        global_config = tmp_path / "global" / "global-config.json"
        _write(global_config, {})  # no update_check key -> first run

        project = tmp_path / "proj" / ".nwave" / "des-config.json"
        _write(
            project,
            {
                "update_check": {
                    "frequency": "daily",
                    "last_checked": "2026-06-15T11:39:25+00:00",
                    "skipped_versions": ["3.18.0"],
                }
            },
        )

        cfg = DESConfig(config_path=project, global_config_path=global_config)

        assert cfg.update_check_frequency is None  # first run from global's view
        assert cfg.update_check_last_checked is None
        assert cfg.update_check_skipped_versions == []

    def test_save_persists_to_global_not_project(self, tmp_path) -> None:
        """save_update_check_state writes to the global config, leaving project untouched."""
        global_config = tmp_path / "global" / "global-config.json"
        global_config.parent.mkdir(parents=True, exist_ok=True)

        project = tmp_path / "proj" / ".nwave" / "des-config.json"
        _write(project, {"rigor": {"profile": "standard"}})

        cfg = DESConfig(config_path=project, global_config_path=global_config)
        cfg.save_update_check_state(
            last_checked="2026-06-15T12:00:00+00:00",
            skipped_versions=["3.18.0"],
            frequency="daily",
        )

        saved_global = json.loads(global_config.read_text(encoding="utf-8"))
        assert (
            saved_global["update_check"]["last_checked"] == "2026-06-15T12:00:00+00:00"
        )
        assert saved_global["update_check"]["skipped_versions"] == ["3.18.0"]
        assert saved_global["update_check"]["frequency"] == "daily"

        # Project file must be untouched (no update_check leaked into it).
        saved_project = json.loads(project.read_text(encoding="utf-8"))
        assert "update_check" not in saved_project
        assert saved_project["rigor"]["profile"] == "standard"
