"""Unit tests for the Codex DES plugin argv contract (US-2 / FM-2).

Single-behavior unit test that pins the contract: ``_build_hook_entry`` MUST
produce a command string whose final argv token is ``pre-tool-use`` so the
shared DES hook adapter dispatches to the pre_tool_use handler instead of
exiting 1 on a missing-argument error.

WHY-NEW-FILE: tests/installer/unit/plugins/test_codex_argv_contract.py
  CLOSEST-EXISTING: tests/installer/unit/plugins/test_codex_des_plugin.py
  EXTENSION-COST: existing file is 18kB / 5 classes scoped to install /
    verify / uninstall / payload-compat. Adding an argv-contract class there
    blurs the file's responsibility split and makes the contract harder to
    locate in regression triage.
  PARALLEL-RATIONALE: the argv contract is a discrete, FM-tracked invariant
    that DDD-4 locks against ``src/des/adapters/drivers/hooks/hook_router.py``.
    Co-locating its test in a 1-class file makes the FM-2 regression net
    trivially greppable and keeps the contract surface explicit.
"""

from __future__ import annotations

import pytest

from scripts.install.plugins.codex_des_plugin import _build_hook_entry


# Valid event tokens accepted by hook_router.py (DDD-4 contract).
_VALID_EVENT_TOKENS: tuple[str, ...] = (
    "pre-tool-use",
    "pre-task",
    "subagent-stop",
    "post-tool-use",
    "pre-write",
    "pre-edit",
    "session-start",
    "subagent-start",
    "deliver-progress",
)


class TestBuildHookEntryArgvContract:
    """``_build_hook_entry`` must terminate the command with the event token."""

    @pytest.mark.parametrize(
        ("python_path", "pythonpath"),
        [
            ("/usr/bin/python3", "/home/tester/.claude/lib/python"),
            ("/opt/local/bin/python3.12", "/Users/dev/.claude/lib/python"),
            ("python3", "$HOME/.claude/lib/python"),
        ],
    )
    def test_pretool_command_ends_with_pre_tool_use_argv_token(
        self, python_path: str, pythonpath: str
    ) -> None:
        """Final argv token MUST be 'pre-tool-use'.

        Without the token, the shared DES adapter exits 1 with
        ``"Missing command argument (pre-tool-use or subagent-stop)"`` on
        every Codex hook fire — the FM-2 root cause.
        """
        entry = _build_hook_entry(python_path, pythonpath)

        # Structural sanity: PreToolUse matcher group with one handler.
        assert entry["hooks"], "matcher group must expose at least one handler"
        command: str = entry["hooks"][0]["command"]

        tokens = command.strip().split()
        assert tokens, f"command must be non-empty; got {command!r}"
        assert tokens[-1] == "pre-tool-use", (
            f"final argv token must be 'pre-tool-use' so the DES adapter "
            f"dispatches to handle_pre_tool_use(); got tail {tokens[-3:]!r} "
            f"(full command: {command!r})"
        )
        # Belt-and-braces: token MUST be a valid event per hook_router.py.
        assert tokens[-1] in _VALID_EVENT_TOKENS
