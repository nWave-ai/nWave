"""Unit tests for `_generate_hook_command` target-aware path resolution.

Issue #40 / per-project-install feature. Hook commands must point at the
*chosen* target's `lib/python` when `--target` selects a non-default location;
they must keep the existing `$HOME/.claude/lib/python` portable form when the
target is the default `~/.claude/` (preserving cross-machine sync semantics).

Driving seam: `DESPlugin._generate_hook_command(context, action)`.
The change is intentionally minimal: branch on `context.claude_dir`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


@pytest.fixture
def test_logger() -> logging.Logger:
    return logging.getLogger("test")


def _make_context(claude_dir: Path, logger: logging.Logger) -> InstallContext:
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=Path("/unused"),
        templates_dir=Path("/unused"),
        logger=logger,
    )


class TestHookCommandTargetAware:
    """When claude_dir is the default ~/.claude, use the portable $HOME form.
    Otherwise emit an absolute path so Claude Code can exec() without a shell.
    """

    def test_default_target_uses_portable_home_form(self, test_logger: logging.Logger):
        plugin = DESPlugin()
        context = _make_context(Path.home() / ".claude", test_logger)

        command = plugin._generate_hook_command(context, action="pre-task")

        assert "$HOME/.claude/lib/python" in command, (
            "Default target must keep the $HOME-portable form for cross-machine "
            "settings.json sync"
        )

    def test_alternate_global_target_uses_absolute_lib_path(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        plugin = DESPlugin()
        alternate = tmp_path / ".claude-nwave"
        context = _make_context(alternate, test_logger)

        command = plugin._generate_hook_command(context, action="pre-task")

        expected_lib = str(alternate / "lib" / "python")
        assert expected_lib in command, (
            f"Non-default target must emit absolute lib path. "
            f"Expected {expected_lib} in: {command}"
        )
        assert "$HOME/.claude/lib/python" not in command, (
            "Non-default target must NOT leak the default $HOME/.claude form"
        )

    def test_project_scoped_target_uses_absolute_lib_path(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        plugin = DESPlugin()
        project_claude = tmp_path / "my-project" / ".claude"
        project_claude.mkdir(parents=True)
        context = _make_context(project_claude, test_logger)

        command = plugin._generate_hook_command(context, action="subagent-stop")

        assert str(project_claude / "lib" / "python") in command
        assert "$HOME/.claude" not in command

    def test_action_token_is_substituted_in_both_branches(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        plugin = DESPlugin()
        default_ctx = _make_context(Path.home() / ".claude", test_logger)
        custom_ctx = _make_context(tmp_path / ".claude-nwave", test_logger)

        for action in ("pre-task", "subagent-stop", "post-tool-use"):
            assert action in plugin._generate_hook_command(default_ctx, action=action)
            assert action in plugin._generate_hook_command(custom_ctx, action=action)
