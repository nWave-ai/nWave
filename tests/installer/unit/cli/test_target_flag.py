"""Unit tests for `--target <path>` argument parsing on `nwave-ai install`
and `nwave-ai uninstall`.

Issue #40 / per-project-install. Driving port:
    nwave-ai install --target <path>
    nwave-ai uninstall --target <path>

What this layer verifies (without running the heavy installer subprocess):
- `--target <path>` is consumed (NOT forwarded to the subprocess as a bare arg
  the installer would not recognise).
- The path is normalised via expanduser + resolve before being applied.
- The chosen path is set as `CLAUDE_CONFIG_DIR` for the install subprocess.
- `--target $HOME` (or any path whose `realpath` equals `realpath $HOME`) is
  rejected at parse time with exit code 2 and no subprocess is launched.
- Omitting `--target` is byte-identical to today's behavior.

The subprocess itself is mocked. Full end-to-end install/uninstall is covered
by the existing installer acceptance suite.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from nwave_ai import cli


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _scrub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure CLAUDE_CONFIG_DIR is not leaked into the test from the host env."""
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)


def _captured_run_script_args() -> dict:
    """Patch _run_script and capture the call args + the env at call time."""
    captured: dict = {"args": None, "claude_config_dir": None}

    def fake_run_script(script_name: str, args: list[str]) -> int:
        captured["args"] = list(args)
        captured["script"] = script_name
        captured["claude_config_dir"] = os.environ.get("CLAUDE_CONFIG_DIR")
        return 0

    return captured, fake_run_script


class TestInstallTargetFlag:
    def test_target_is_consumed_and_not_forwarded(self, tmp_path: Path):
        captured, fake = _captured_run_script_args()
        target = tmp_path / ".claude-nwave"
        with (
            patch.object(cli, "_run_script", side_effect=fake),
            patch.object(
                cli, "handle_install_density_prompt", return_value="default_silent"
            ),
        ):
            rc = cli._handle_install(["--target", str(target), "--yes"])
        assert rc == 0
        assert captured["args"] is not None
        assert "--target" not in captured["args"]
        assert str(target) not in captured["args"]

    def test_target_sets_claude_config_dir_env(self, tmp_path: Path):
        captured, fake = _captured_run_script_args()
        target = tmp_path / ".claude-nwave"
        with (
            patch.object(cli, "_run_script", side_effect=fake),
            patch.object(
                cli, "handle_install_density_prompt", return_value="default_silent"
            ),
        ):
            cli._handle_install(["--target", str(target), "--yes"])
        assert captured["claude_config_dir"] == str(target.resolve())

    def test_target_with_user_expansion(self, tmp_path: Path, monkeypatch):
        captured, fake = _captured_run_script_args()
        monkeypatch.setenv("HOME", str(tmp_path))
        with (
            patch.object(cli, "_run_script", side_effect=fake),
            patch.object(
                cli, "handle_install_density_prompt", return_value="default_silent"
            ),
        ):
            cli._handle_install(["--target", "~/.claude-nwave", "--yes"])
        # ~/.claude-nwave is resolved against the HOME we just set
        assert captured["claude_config_dir"] == str(
            (tmp_path / ".claude-nwave").resolve()
        )

    def test_target_relative_path_is_resolved_absolute(
        self, tmp_path: Path, monkeypatch
    ):
        captured, fake = _captured_run_script_args()
        monkeypatch.chdir(tmp_path)
        with (
            patch.object(cli, "_run_script", side_effect=fake),
            patch.object(
                cli, "handle_install_density_prompt", return_value="default_silent"
            ),
        ):
            cli._handle_install(["--target", "./.claude", "--yes"])
        assert captured["claude_config_dir"] == str((tmp_path / ".claude").resolve())

    def test_target_equal_to_home_is_refused(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setenv("HOME", str(tmp_path))
        with patch.object(cli, "_run_script") as run_script:
            rc = cli._handle_install(["--target", str(tmp_path), "--yes"])
        assert rc == 2
        run_script.assert_not_called()
        err = capsys.readouterr().err
        assert "must point to a Claude config directory" in err.lower() or (
            "home directory" in err.lower()
        )

    def test_target_resolving_to_home_is_refused(
        self, tmp_path: Path, monkeypatch, capsys
    ):
        """A relative path that resolves to $HOME (e.g. '.') must be refused."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        with patch.object(cli, "_run_script") as run_script:
            rc = cli._handle_install(["--target", ".", "--yes"])
        assert rc == 2
        run_script.assert_not_called()

    def test_omitting_target_does_not_set_claude_config_dir(self, tmp_path: Path):
        captured, fake = _captured_run_script_args()
        with (
            patch.object(cli, "_run_script", side_effect=fake),
            patch.object(
                cli, "handle_install_density_prompt", return_value="default_silent"
            ),
        ):
            cli._handle_install(["--yes"])
        assert captured["claude_config_dir"] is None, (
            "Default behavior must not set CLAUDE_CONFIG_DIR; existing env-var "
            "semantics still apply"
        )


class TestUninstallTargetFlag:
    def test_uninstall_target_is_consumed_and_sets_env(self, tmp_path: Path):
        captured, fake = _captured_run_script_args()
        target = tmp_path / ".claude-nwave"
        with patch.object(cli, "_run_script", side_effect=fake):
            rc = cli._handle_uninstall(["--target", str(target), "--force"])
        assert rc == 0
        assert captured["script"] == "uninstall_nwave.py"
        assert "--target" not in captured["args"]
        assert str(target) not in captured["args"]
        assert captured["claude_config_dir"] == str(target.resolve())

    def test_uninstall_target_equal_to_home_is_refused(
        self, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        with patch.object(cli, "_run_script") as run_script:
            rc = cli._handle_uninstall(["--target", str(tmp_path)])
        assert rc == 2
        run_script.assert_not_called()

    def test_omitting_target_in_uninstall_is_byte_compatible(self):
        captured, fake = _captured_run_script_args()
        with patch.object(cli, "_run_script", side_effect=fake):
            cli._handle_uninstall(["--force"])
        assert captured["claude_config_dir"] is None
        assert captured["args"] == ["--force"]
