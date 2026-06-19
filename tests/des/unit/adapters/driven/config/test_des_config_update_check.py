"""Unit tests for DESConfig update_check properties and save method.

update_check state (frequency, last_checked, skipped_versions) is machine-scoped:
it is read from and written to the GLOBAL config (~/.nwave/global-config.json),
not the per-project des-config.json. These tests therefore inject a
``global_config_path`` and assert reads/writes against it.

Test Budget: 6 behaviors x 2 = 12 max. Actual: 10 tests (1 parametrized).

Behaviors:
1. update_check_frequency returns None when update_check key is entirely absent
2. update_check_frequency returns 'daily' when key present but frequency absent
3. update_check_last_checked defaults to None when key absent
4. update_check_skipped_versions defaults to empty list when key absent
5. save_update_check_state writes frequency, last_checked, skipped_versions
6. save_update_check_state preserves unrelated config keys (read-modify-write)
"""

import json

import pytest

from des.adapters.driven.config.des_config import DESConfig


def _global_config(tmp_path, content: dict | None) -> DESConfig:
    """Return a DESConfig whose global config holds the given update_check data.

    When ``content`` is None the global file is absent (first-run scenario).
    The project config is always empty, proving update_check ignores it.
    """
    global_path = tmp_path / "global-config.json"
    if content is not None:
        global_path.write_text(json.dumps(content), encoding="utf-8")
    project_path = tmp_path / ".nwave" / "des-config.json"
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text("{}", encoding="utf-8")
    return DESConfig(config_path=project_path, global_config_path=global_path)


class TestUpdateCheckFrequencyDefault:
    """update_check_frequency contract: None when key absent, 'daily' when key present."""

    @pytest.mark.parametrize(
        "global_content",
        [
            {},
            {"rigor": {"profile": "standard"}},
        ],
        ids=["empty_config", "no_update_check_key"],
    )
    def test_returns_none_when_update_check_key_entirely_absent(
        self, tmp_path, global_content
    ) -> None:
        """update_check_frequency returns None when update_check key is absent (first run)."""
        config = _global_config(tmp_path, global_content)

        assert config.update_check_frequency is None

    def test_returns_none_when_global_config_file_missing(self, tmp_path) -> None:
        """update_check_frequency returns None when global config does not exist (first run)."""
        config = _global_config(tmp_path, None)

        assert config.update_check_frequency is None

    def test_returns_daily_when_update_check_key_present_but_frequency_absent(
        self, tmp_path
    ) -> None:
        """update_check_frequency defaults to 'daily' when key exists but frequency absent."""
        config = _global_config(tmp_path, {"update_check": {}})

        assert config.update_check_frequency == "daily"

    def test_returns_configured_frequency_when_set(self, tmp_path) -> None:
        """update_check_frequency returns value from global config when explicitly set."""
        config = _global_config(tmp_path, {"update_check": {"frequency": "weekly"}})

        assert config.update_check_frequency == "weekly"


class TestUpdateCheckLastCheckedDefault:
    """update_check_last_checked returns None when key is absent."""

    def test_returns_none_when_global_config_file_missing(self, tmp_path) -> None:
        """update_check_last_checked returns None when global config does not exist."""
        config = _global_config(tmp_path, None)

        assert config.update_check_last_checked is None

    def test_returns_none_when_update_check_key_absent(self, tmp_path) -> None:
        """update_check_last_checked returns None when update_check key is absent."""
        config = _global_config(tmp_path, {"audit_logging_enabled": True})

        assert config.update_check_last_checked is None

    def test_returns_iso_string_when_set(self, tmp_path) -> None:
        """update_check_last_checked returns ISO 8601 string when explicitly set."""
        config = _global_config(
            tmp_path, {"update_check": {"last_checked": "2026-02-25T10:00:00Z"}}
        )

        assert config.update_check_last_checked == "2026-02-25T10:00:00Z"


class TestUpdateCheckSkippedVersionsDefault:
    """update_check_skipped_versions returns empty list when key is absent."""

    def test_returns_empty_list_when_global_config_file_missing(self, tmp_path) -> None:
        """update_check_skipped_versions returns [] when global config does not exist."""
        config = _global_config(tmp_path, None)

        assert config.update_check_skipped_versions == []

    def test_returns_list_of_skipped_versions_when_set(self, tmp_path) -> None:
        """update_check_skipped_versions returns configured list when set."""
        config = _global_config(
            tmp_path, {"update_check": {"skipped_versions": ["2.0.0", "2.1.0"]}}
        )

        assert config.update_check_skipped_versions == ["2.0.0", "2.1.0"]


class TestUpdateCheckLatestAvailable:
    """update_check_latest_available reads the latest discovered version."""

    def test_returns_latest_available_when_set(self, tmp_path) -> None:
        config = _global_config(
            tmp_path, {"update_check": {"latest_available": "3.18.0"}}
        )

        assert config.update_check_latest_available == "3.18.0"

    def test_returns_none_when_absent(self, tmp_path) -> None:
        config = _global_config(tmp_path, {"update_check": {}})

        assert config.update_check_latest_available is None


class TestSaveUpdateCheckState:
    """save_update_check_state writes state to the global config file."""

    def test_persists_latest_available_when_provided(self, tmp_path) -> None:
        """save_update_check_state records latest_available for /nw-update."""
        config = _global_config(tmp_path, None)
        config.save_update_check_state(
            last_checked="2026-06-15T10:00:00Z",
            skipped_versions=[],
            latest_available="3.18.0",
        )

        saved = json.loads((tmp_path / "global-config.json").read_text())
        assert saved["update_check"]["latest_available"] == "3.18.0"

    def test_preserves_latest_available_when_none_passed(self, tmp_path) -> None:
        """A later save without latest_available must not wipe a stored value."""
        config = _global_config(
            tmp_path, {"update_check": {"latest_available": "3.18.0"}}
        )
        config.save_update_check_state(
            last_checked="2026-06-15T11:00:00Z",
            skipped_versions=[],
        )

        saved = json.loads((tmp_path / "global-config.json").read_text())
        assert saved["update_check"]["latest_available"] == "3.18.0"

    def test_writes_all_fields_when_file_does_not_exist(self, tmp_path) -> None:
        """save_update_check_state creates update_check key in the global config."""
        config = _global_config(tmp_path, None)
        config.save_update_check_state(
            last_checked="2026-02-25T10:00:00Z",
            skipped_versions=["2.0.0"],
            frequency="weekly",
        )

        saved = json.loads((tmp_path / "global-config.json").read_text())
        assert saved["update_check"]["last_checked"] == "2026-02-25T10:00:00Z"
        assert saved["update_check"]["skipped_versions"] == ["2.0.0"]
        assert saved["update_check"]["frequency"] == "weekly"

    def test_preserves_existing_frequency_when_none_passed(self, tmp_path) -> None:
        """save_update_check_state preserves frequency when None passed."""
        config = _global_config(tmp_path, {"update_check": {"frequency": "weekly"}})
        config.save_update_check_state(
            last_checked="2026-02-25T10:00:00Z",
            skipped_versions=[],
            frequency=None,
        )

        saved = json.loads((tmp_path / "global-config.json").read_text())
        assert saved["update_check"]["frequency"] == "weekly"
        assert saved["update_check"]["last_checked"] == "2026-02-25T10:00:00Z"

    def test_preserves_unrelated_global_config_keys(self, tmp_path) -> None:
        """save_update_check_state does not modify unrelated global config keys."""
        config = _global_config(
            tmp_path,
            {
                "attribution": {"enabled": True},
                "rigor": {"profile": "standard"},
            },
        )
        config.save_update_check_state(
            last_checked="2026-02-25T10:00:00Z",
            skipped_versions=[],
        )

        saved = json.loads((tmp_path / "global-config.json").read_text())
        assert saved["attribution"]["enabled"] is True
        assert saved["rigor"]["profile"] == "standard"
        assert saved["update_check"]["last_checked"] == "2026-02-25T10:00:00Z"
