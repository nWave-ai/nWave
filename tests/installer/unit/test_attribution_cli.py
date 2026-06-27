"""Unit tests for CLI attribution subcommand.

Tests validate on/off/status commands through the driving port
(cli.main) and assert at driven port boundaries (global-config.json +
~/.claude/settings.json).

Test Budget: 6 behaviors x 2 = 12 max. Using 6 tests.

Behaviors tested:
1. 'attribution on' -> enables preference + registers the commit hook, NO
   settings.json credit written (ADR-CA-007: the hook is the sole mechanism)
2. 'attribution off' -> disables preference + removes settings.json credit
3. 'attribution status' when enabled -> shows "on"
4. 'attribution status' when disabled -> shows "off"
5. Toggle off delegates legacy cleanup to migrate_legacy_settings_attribution
   (legacy-residue cleanup is RETAINED on 'off', routed via the claude_dir seam)
6. Enable -> registers the hook and writes NO managed credit

Post-migration (ADR-CA-007): the settings.json attribution write surface is
RETIRED. 'on' registers the activation-gated PreToolUse commit-attribution hook
as the sole mechanism and never writes attribution.{commit,pr}. 'off' still
removes any legacy settings credit (cleanup) and unregisters the hook.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from nwave_ai.cli import main


# Serialize tests touching .git/hooks/ to avoid xdist races on shared state.
pytestmark = pytest.mark.xdist_group("git_hooks")


def _write_config(config_dir: Path, *, enabled: bool) -> None:
    """Write global-config.json with attribution preference."""
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "global-config.json"
    config_file.write_text(
        json.dumps(
            {
                "attribution": {
                    "enabled": enabled,
                    "trailer": "Co-Authored-By: nWave <nwave@nwave.ai>",
                }
            }
        ),
        encoding="utf-8",
    )


def _read_config(config_dir: Path) -> dict:
    """Read global-config.json."""
    config_file = config_dir / "global-config.json"
    with open(config_file, encoding="utf-8") as f:
        return json.load(f)


class TestAttributionCLI:
    """Tests for nwave-ai attribution on/off/status."""

    def test_attribution_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        """'attribution on' enables the preference + registers the hook, writing
        NO settings.json credit (ADR-CA-007: the hook is the sole mechanism)."""
        nwave_dir = tmp_path / ".nwave"
        home_dir = tmp_path / "home"
        claude_dir = home_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))

        with (
            patch("sys.argv", ["nwave-ai", "attribution", "on"]),
            patch("nwave_ai.cli._get_config_dir", return_value=nwave_dir),
        ):
            result = main()

        assert result == 0
        config = _read_config(nwave_dir)
        assert config["attribution"]["enabled"] is True

        # No managed credit written to settings.json (retired surface).
        settings = json.loads((claude_dir / "settings.json").read_text())
        assert "commit" not in settings.get("attribution", {})

        # The commit-attribution hook IS registered (sole mechanism).
        commands = [
            hook.get("command", "")
            for entry in settings.get("hooks", {}).get("PreToolUse", [])
            for hook in entry.get("hooks", [])
        ]
        assert any("pre-commit-attribution" in c for c in commands)

        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()

    def test_attribution_off(self, tmp_path: Path, capsys) -> None:
        """'attribution off' disables attribution in config."""
        nwave_dir = tmp_path / ".nwave"
        _write_config(nwave_dir, enabled=True)

        with (
            patch("sys.argv", ["nwave-ai", "attribution", "off"]),
            patch("nwave_ai.cli._get_config_dir", return_value=nwave_dir),
            patch("nwave_ai.cli.migrate_legacy_settings_attribution"),
        ):
            result = main()

        assert result == 0
        config = _read_config(nwave_dir)
        assert config["attribution"]["enabled"] is False
        captured = capsys.readouterr()
        assert "disabled" in captured.out.lower()

    def test_attribution_status_enabled(self, tmp_path: Path, capsys) -> None:
        """'attribution status' shows 'on' when enabled."""
        nwave_dir = tmp_path / ".nwave"
        _write_config(nwave_dir, enabled=True)

        with (
            patch("sys.argv", ["nwave-ai", "attribution", "status"]),
            patch("nwave_ai.cli._get_config_dir", return_value=nwave_dir),
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "on" in captured.out.lower()

    def test_attribution_status_disabled(self, tmp_path: Path, capsys) -> None:
        """'attribution status' shows 'off' when disabled."""
        nwave_dir = tmp_path / ".nwave"
        _write_config(nwave_dir, enabled=False)

        with (
            patch("sys.argv", ["nwave-ai", "attribution", "status"]),
            patch("nwave_ai.cli._get_config_dir", return_value=nwave_dir),
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "off" in captured.out.lower()

    def test_off_delegates_to_legacy_migration(self, tmp_path: Path) -> None:
        """'attribution off' delegates legacy cleanup to the migration helper.

        ADR-CA-007 retires the WRITE surface but RETAINS legacy-residue cleanup
        on 'off': turning attribution off must scrub any pre-existing managed
        credit from settings.json. As of 01-03 that cleanup is the one-shot
        ``migrate_legacy_settings_attribution`` (which reuses the settings
        remover internally), routed through the claude_dir seam."""
        nwave_dir = tmp_path / ".nwave"
        _write_config(nwave_dir, enabled=True)

        migrate_calls = []

        def mock_migrate(config_dir=None, claude_dir=None):
            migrate_calls.append((config_dir, claude_dir))
            return False

        with (
            patch("sys.argv", ["nwave-ai", "attribution", "off"]),
            patch("nwave_ai.cli._get_config_dir", return_value=nwave_dir),
            patch(
                "nwave_ai.cli.migrate_legacy_settings_attribution",
                side_effect=mock_migrate,
            ),
        ):
            main()

        assert _read_config(nwave_dir)["attribution"]["enabled"] is False
        assert len(migrate_calls) == 1
        # Cleanup routed through the claude_dir injection seam (criterion 3).
        assert migrate_calls[0][1] is not None

    def test_enable_writes_no_managed_credit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        """'attribution on' registers the hook and writes NO managed credit.

        ADR-CA-007 retires the settings.json write surface: enabling must NOT
        produce an attribution.commit entry — the registered hook is the sole
        mechanism."""
        nwave_dir = tmp_path / ".nwave"
        _write_config(nwave_dir, enabled=False)
        home_dir = tmp_path / "home"
        claude_dir = home_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))

        with (
            patch("sys.argv", ["nwave-ai", "attribution", "on"]),
            patch("nwave_ai.cli._get_config_dir", return_value=nwave_dir),
        ):
            result = main()

        assert result == 0
        assert _read_config(nwave_dir)["attribution"]["enabled"] is True

        settings = json.loads((claude_dir / "settings.json").read_text())
        assert "commit" not in settings.get("attribution", {})
        commands = [
            hook.get("command", "")
            for entry in settings.get("hooks", {}).get("PreToolUse", [])
            for hook in entry.get("hooks", [])
        ]
        assert any("pre-commit-attribution" in c for c in commands)
