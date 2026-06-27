"""Regression tests: attribution install must NEVER prompt interactively.

Root cause (Fabio RCA, 2026-04-16, macOS + Python 3.14):
    AttributionPlugin._do_install() called builtins.input(_PROMPT) whenever
    stdin was a TTY and no preference existed. An interactive prompt inside
    an install command is wrong by design -- install is invoked from CI,
    Docker, SessionStart hooks, and other non-interactive automation
    contexts. Ctrl-C during the prompt surfaced as a KeyboardInterrupt
    crash; worse, the soon-to-ship auto-update-deferred feature triggers
    `nwave-ai install` from the SessionStart hook, where a blocking prompt
    would deadlock the session.

Fix (user-approved "opt-in default with opt-out suggestion"):
    - Install NEVER calls input(); defaults to enabled=True on new installs
    - Existing preferences (True or False) are preserved unchanged
    - A clear message is printed once on first-time enablement
      pointing users at `nwave-ai attribution off` to opt out

Each test below fails on the pre-fix code path (either because input() is
called, or because the preference is flipped, or both).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.install.plugins.attribution_plugin import AttributionPlugin
from scripts.install.plugins.base import InstallContext


# Serialize tests touching .git/hooks/ to avoid xdist races on shared state.
pytestmark = pytest.mark.xdist_group("git_hooks")


@pytest.fixture(autouse=True)
def _isolate_attribution_side_effects():
    """Prevent the plugin from touching ~/.claude/settings.json or probing git.

    Post-ADR-CA-007 install no longer WRITES the settings.json attribution
    credit (that surface is retired): it registers the activation-gated
    PreToolUse hook and migrates the legacy hook. Both real-FS side effects are
    stubbed so the non-blocking regression assertions exercise only the
    prompt-free control flow. ``register_attribution_hook`` is the symbol the
    plugin still imports (``write_settings_attribution`` no longer exists on the
    plugin module), so the patch re-points onto it.
    """
    with (
        patch(
            "scripts.install.plugins.attribution_plugin.register_attribution_hook",
            return_value=True,
        ),
        patch(
            "scripts.install.plugins.attribution_plugin.migrate_legacy_hook",
            return_value=False,
        ),
    ):
        yield


@pytest.fixture
def _input_must_not_be_called():
    """Patch builtins.input to raise if ever called.

    Any test reaching input() fails with a clear message -- this is the
    strongest possible assertion that the install flow is non-blocking.
    """

    def _boom(*_args, **_kwargs):
        raise AssertionError(
            "builtins.input() was called during install -- "
            "install must be non-blocking (Fabio RCA regression)"
        )

    with patch("builtins.input", side_effect=_boom) as mock_input:
        yield mock_input


def _make_context(tmp_path: Path) -> InstallContext:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    logger = MagicMock()
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=tmp_path / "templates",
        logger=logger,
        project_root=tmp_path / "project",
        metadata={"nwave_config_dir": tmp_path / ".nwave"},
    )


def _logger_messages(context: InstallContext) -> str:
    """Collect every message passed to context.logger (info/warn/etc)."""
    parts: list[str] = []
    for method_name in ("info", "warn", "warning", "debug", "error"):
        method = getattr(context.logger, method_name, None)
        if method is None:
            continue
        for call in method.call_args_list:
            if call.args:
                parts.append(str(call.args[0]))
    return "\n".join(parts)


def _read_config(nwave_dir: Path) -> dict:
    with open(nwave_dir / "global-config.json", encoding="utf-8") as f:
        return json.load(f)


class TestAttributionInstallIsNonBlocking:
    """Install must never prompt -- regression for Fabio RCA."""

    def test_install_no_prompt_with_tty_no_existing_preference(
        self, tmp_path: Path, _input_must_not_be_called
    ) -> None:
        """TTY + no preference: default opt-in, no prompt, helpful message."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        plugin = AttributionPlugin(config_dir=nwave_dir)

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = plugin.install(context)

        assert result.success is True
        _input_must_not_be_called.assert_not_called()

        config = _read_config(nwave_dir)
        assert config["attribution"]["enabled"] is True

        messages = _logger_messages(context).lower()
        assert "attribution" in messages and "enabled" in messages
        assert "nwave-ai attribution off" in messages

    def test_install_no_prompt_with_non_tty_ci_context(
        self, tmp_path: Path, _input_must_not_be_called
    ) -> None:
        """No TTY (CI/Docker/hook): same default-on path, no prompt."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        plugin = AttributionPlugin(config_dir=nwave_dir)

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            result = plugin.install(context)

        assert result.success is True
        _input_must_not_be_called.assert_not_called()

        config = _read_config(nwave_dir)
        assert config["attribution"]["enabled"] is True

    def test_install_preserves_existing_enabled_preference(
        self, tmp_path: Path, _input_must_not_be_called
    ) -> None:
        """Re-install with enabled=True: unchanged, no prompt."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        (nwave_dir / "global-config.json").write_text(
            json.dumps(
                {
                    "attribution": {
                        "enabled": True,
                        "trailer": "Co-Authored-By: nWave <nwave@nwave.ai>",
                    }
                }
            ),
            encoding="utf-8",
        )

        plugin = AttributionPlugin(config_dir=nwave_dir)
        result = plugin.install(context)

        assert result.success is True
        _input_must_not_be_called.assert_not_called()
        assert _read_config(nwave_dir)["attribution"]["enabled"] is True

    def test_install_preserves_existing_disabled_preference(
        self, tmp_path: Path, _input_must_not_be_called
    ) -> None:
        """Re-install with enabled=False: MUST stay False (no flip to default)."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        (nwave_dir / "global-config.json").write_text(
            json.dumps(
                {
                    "attribution": {
                        "enabled": False,
                        "trailer": "Co-Authored-By: nWave <nwave@nwave.ai>",
                    }
                }
            ),
            encoding="utf-8",
        )

        plugin = AttributionPlugin(config_dir=nwave_dir)
        result = plugin.install(context)

        assert result.success is True
        _input_must_not_be_called.assert_not_called()
        assert _read_config(nwave_dir)["attribution"]["enabled"] is False

    def test_install_never_hits_keyboard_interrupt_path(self, tmp_path: Path) -> None:
        """Canonical proof: Fabio's Ctrl-C crash path is closed by design.

        Patches input() to raise KeyboardInterrupt. If the production code
        ever calls input() again (regression), this test raises and fails.
        Because input() is never called, KeyboardInterrupt cannot occur,
        and install completes with success=True.
        """
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", side_effect=KeyboardInterrupt),
        ):
            mock_stdin.isatty.return_value = True
            # MUST NOT raise KeyboardInterrupt -- input() must never be called
            result = plugin.install(context)

        assert result.success is True
        assert _read_config(nwave_dir)["attribution"]["enabled"] is True
