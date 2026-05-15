"""Unit tests for Codex CLI DES hook installer plugin.

Tests validate that:
- validate_prerequisites() skips gracefully when Codex CLI is not detected
- validate_prerequisites() fails when Codex is detected but DES module missing
- install() writes a PreToolUse hook entry into ~/.codex/hooks.json
- install() writes a manifest tracking the installed hook config
- verify() returns success after a successful install
- uninstall() removes only nWave DES hook entries, preserving user hooks

Tests follow hexagonal architecture - mocks only at port boundaries.
The state-delta paradigm guards multi-slot mutations (hooks.json content +
manifest presence + user-hook preservation).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.codex_des_plugin import CodexDESPlugin


if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_context(
    tmp_path: Path,
    *,
    des_module_exists: bool = True,
) -> InstallContext:
    """Create an InstallContext with a configurable DES module presence."""
    project_root = tmp_path / "project"
    framework_source = project_root / "nWave"
    framework_source.mkdir(parents=True)

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    if des_module_exists:
        des_dir = claude_dir / "lib" / "python" / "des"
        des_dir.mkdir(parents=True)
        (des_dir / "__init__.py").write_text("", encoding="utf-8")

    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts",
        templates_dir=framework_source / "templates",
        logger=MagicMock(),
        project_root=project_root,
        framework_source=framework_source,
    )


def _patch_codex_config_dir(monkeypatch, codex_config_dir: Path) -> None:
    """Redirect _codex_config_dir() to a tmp path."""
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin._codex_config_dir",
        lambda: codex_config_dir,
    )


def _patch_path_resolvers(monkeypatch) -> None:
    """Force deterministic Python and PYTHONPATH resolution."""
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin.resolve_python_command_for_spawn",
        lambda: "/usr/bin/python3",
    )
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin.resolve_des_lib_path_for_spawn",
        lambda: "/home/tester/.claude/lib/python",
    )


def _patch_codex_binary_absent(monkeypatch) -> None:
    """Force shutil.which('codex') to return None inside the plugin."""
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin._shutil.which",
        lambda _name: None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidatePrerequisites:
    """validate_prerequisites: skip / fail / proceed branches."""

    def test_skips_gracefully_when_codex_not_detected(self, tmp_path, monkeypatch):
        """
        GIVEN: ~/.codex/ does not exist AND `codex` not in PATH
        WHEN: validate_prerequisites() runs
        THEN: Returns success with skip message
        """
        context = _make_context(tmp_path)
        codex_config_dir = tmp_path / "home" / ".codex"  # does NOT exist
        _patch_codex_config_dir(monkeypatch, codex_config_dir)
        _patch_codex_binary_absent(monkeypatch)

        plugin = CodexDESPlugin()
        result = plugin.validate_prerequisites(context)

        assert result.success is True
        assert (
            "skip" in result.message.lower() or "not detected" in result.message.lower()
        )

    def test_fails_when_codex_present_but_des_module_missing(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN: Codex is detected (~/.codex/ exists) but DES Python module is NOT
        WHEN: validate_prerequisites() runs
        THEN: Returns failure citing the DES module
        """
        context = _make_context(tmp_path, des_module_exists=False)
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_config_dir(monkeypatch, codex_config_dir)

        plugin = CodexDESPlugin()
        result = plugin.validate_prerequisites(context)

        assert result.success is False
        assert "des" in result.message.lower()


class TestInstallWritesHooksJsonAndManifest:
    """install: writes hooks.json with the nWave DES entry + manifest."""

    def test_install_creates_hooks_json_and_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: Codex detected and DES module installed
        WHEN: install() runs (no prior hooks.json)
        THEN: hooks.json contains exactly one nWave DES entry pointing to the
              claude_code_hook_adapter, and the manifest exists.
        """
        context = _make_context(tmp_path)
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_config_dir(monkeypatch, codex_config_dir)
        _patch_path_resolvers(monkeypatch)

        hooks_path = codex_config_dir / "hooks.json"
        manifest_path = codex_config_dir / ".nwave-des-manifest.json"

        tracked = {"hooks.exists", "manifest.exists"}

        def snapshot() -> dict[str, object]:
            return {
                "hooks.exists": hooks_path.is_file(),
                "manifest.exists": manifest_path.is_file(),
            }

        before = snapshot()

        plugin = CodexDESPlugin()
        result = plugin.install(context)

        after = snapshot()

        assert result.success is True
        assert_state_delta(
            before,
            after,
            universe=tracked,
            expected={
                "hooks.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )

        # Verify hooks.json content shape and command wiring.
        # Schema per DDD-1 (codex-empirical-e2e-support, 2026-05-13): event-keyed
        # object root — {"hooks": {"PreToolUse": [<matcher-group>, ...]}}.
        doc = json.loads(hooks_path.read_text(encoding="utf-8"))
        assert isinstance(doc, dict)
        assert isinstance(doc.get("hooks"), dict)
        pretool = doc["hooks"].get("PreToolUse")
        assert isinstance(pretool, list)
        assert len(pretool) == 1
        entry = pretool[0]
        # Narrow matcher: only Codex-real tools trigger DES validation.
        # DDD-6 (refined by DDD-8 spike Q6, 2026-05-13) restricts the
        # whitelist to {Bash, apply_patch}. The pre-FM-3 value
        # "^Task$|^Bash$" referenced "Task" — a Claude-Code-only tool name
        # Codex never emits in PreToolUse — and was corrected at step 01-03.
        assert entry["matcher"] == "^Bash$|^apply_patch$"
        command = entry["hooks"][0]["command"]
        assert "claude_code_hook_adapter" in command
        assert "/usr/bin/python3" in command
        assert "/home/tester/.claude/lib/python" in command

    def test_reinstall_does_not_duplicate_nwave_entries(self, tmp_path, monkeypatch):
        """
        GIVEN: A prior install left one nWave DES entry in hooks.json
            AND a user-created hook entry is also present
        WHEN: install() runs again
        THEN: The user entry is preserved AND there is still exactly one
              nWave DES entry (no duplication on reinstall).
        """
        context = _make_context(tmp_path)
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_config_dir(monkeypatch, codex_config_dir)
        _patch_path_resolvers(monkeypatch)

        plugin = CodexDESPlugin()
        plugin.install(context)

        # Prepend a user-created hook entry into the event-keyed PreToolUse list.
        # DDD-1: root is an object with "hooks.PreToolUse" list of matcher groups.
        hooks_path = codex_config_dir / "hooks.json"
        doc = json.loads(hooks_path.read_text(encoding="utf-8"))
        doc["hooks"].setdefault("PreToolUse", []).insert(
            0,
            {
                "matcher": "^Bash$",
                "hooks": [
                    {
                        "type": "command",
                        "command": "/usr/bin/echo user-hook",
                        "timeout": 10,
                    }
                ],
            },
        )
        hooks_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

        # Reinstall
        result = plugin.install(context)
        assert result.success is True

        final_doc = json.loads(hooks_path.read_text(encoding="utf-8"))
        pretool = final_doc["hooks"]["PreToolUse"]
        nwave_entries = [
            e
            for e in pretool
            if any(
                "claude_code_hook_adapter" in h.get("command", "")
                for h in e.get("hooks", [])
            )
        ]
        user_entries = [
            e
            for e in pretool
            if any("echo user-hook" in h.get("command", "") for h in e.get("hooks", []))
        ]
        assert len(nwave_entries) == 1, "nWave DES entry must not duplicate"
        assert len(user_entries) == 1, "User hook must be preserved"


class TestVerify:
    """verify: success after install."""

    def test_verify_passes_after_install(self, tmp_path, monkeypatch):
        """
        GIVEN: A successful install
        WHEN: verify() runs
        THEN: Returns success
        """
        context = _make_context(tmp_path)
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_config_dir(monkeypatch, codex_config_dir)
        _patch_path_resolvers(monkeypatch)

        plugin = CodexDESPlugin()
        plugin.install(context)
        result = plugin.verify(context)

        assert result.success is True


class TestUninstallPreservesUserHooks:
    """uninstall: removes only nWave DES entries; user hooks survive."""

    def test_uninstall_preserves_user_hook_entries(self, tmp_path, monkeypatch):
        """
        GIVEN: hooks.json contains one nWave DES entry AND one user hook
        WHEN: uninstall() runs
        THEN: The user hook remains, the nWave entry is removed,
              and the manifest is deleted.
        """
        context = _make_context(tmp_path)
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_config_dir(monkeypatch, codex_config_dir)
        _patch_path_resolvers(monkeypatch)

        plugin = CodexDESPlugin()
        plugin.install(context)

        hooks_path = codex_config_dir / "hooks.json"
        manifest_path = codex_config_dir / ".nwave-des-manifest.json"

        # Add a user-created hook on the event-keyed PreToolUse list (DDD-1).
        doc = json.loads(hooks_path.read_text(encoding="utf-8"))
        doc["hooks"].setdefault("PreToolUse", []).append(
            {
                "matcher": "^Bash$",
                "hooks": [
                    {
                        "type": "command",
                        "command": "/usr/bin/echo user-hook",
                        "timeout": 10,
                    }
                ],
            }
        )
        hooks_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

        tracked = {
            "manifest.exists",
            "user_hook.present",
            "nwave_hook.present",
        }

        def snapshot() -> dict[str, object]:
            # DDD-1 event-keyed schema: walk every event's matcher-group list.
            if hooks_path.exists():
                doc = json.loads(hooks_path.read_text(encoding="utf-8"))
                events = doc.get("hooks", {}) if isinstance(doc, dict) else {}
                groups = [
                    entry
                    for entries in events.values()
                    if isinstance(entries, list)
                    for entry in entries
                ]
            else:
                groups = []
            user_present = any(
                any(
                    "echo user-hook" in h.get("command", "") for h in e.get("hooks", [])
                )
                for e in groups
            )
            nwave_present = any(
                any(
                    "claude_code_hook_adapter" in h.get("command", "")
                    for h in e.get("hooks", [])
                )
                for e in groups
            )
            return {
                "manifest.exists": manifest_path.is_file(),
                "user_hook.present": user_present,
                "nwave_hook.present": nwave_present,
            }

        before = snapshot()
        assert before == {
            "manifest.exists": True,
            "user_hook.present": True,
            "nwave_hook.present": True,
        }

        result = plugin.uninstall(context)

        after = snapshot()

        assert result.success is True
        assert_state_delta(
            before,
            after,
            universe=tracked,
            expected={
                "manifest.exists": set_to(False),
                "nwave_hook.present": set_to(False),
                # user_hook.present implicit-unchanged
            },
        )


class TestCodexHookPayloadCompatibility:
    """Empirical payload compatibility: Codex hook JSON shape vs Claude Code.

    Finding (2026-05-05, Issue 3):

    Claude Code PreToolUse payload includes ``transcript_path``; Codex's
    equivalent does not. The DES adapter reads only ``tool_input`` (and its
    sub-keys ``prompt``, ``subagent_type``) from the PreToolUse payload — it
    never accesses ``transcript_path`` — so both shapes are accepted without
    any translation shim.

    For the SubagentStop / Stop boundary there IS a field-name gap:
    Claude Code sends ``agent_transcript_path``; Codex's ``Stop`` hook sends
    ``transcript_path`` (different key).  The DES subagent-stop handler calls
    ``hook_input.get("agent_transcript_path")`` which returns None on a Codex
    payload, causing the handler to fall through to ``{"decision": "allow"}``
    (graceful pass-through, no crash).

    These tests document both behaviours so future adapters know the exact gap.
    """

    def _invoke_pre_tool_use_handler(self, payload: dict) -> tuple[int, str]:
        """Run handle_pre_tool_use() with a custom stdin payload.

        Patches:
        - sys.stdin: supplies the JSON payload
        - hook_protocol._audit_writer_factory: returns NullAuditLogWriter
        - service_factory.create_pre_tool_use_service: returns allow-all stub

        Returns:
            (exit_code, stdout_text)
        """
        import io
        from unittest.mock import MagicMock, patch

        from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter
        from des.adapters.drivers.hooks import hook_protocol, service_factory
        from des.adapters.drivers.hooks.pre_tool_use_handler import handle_pre_tool_use
        from des.ports.driver_ports.pre_tool_use_port import HookDecision

        stdin_data = json.dumps(payload)
        captured_stdout = io.StringIO()

        # Stub service returns allow for any input — we are testing the
        # payload parsing layer, not the enforcement logic.
        allow_decision = HookDecision(action="allow", reason="stub allow")
        stub_service = MagicMock()
        stub_service.validate.return_value = allow_decision

        with (
            patch("sys.stdin", io.StringIO(stdin_data)),
            patch("sys.stdout", captured_stdout),
            patch.object(
                hook_protocol,
                "_audit_writer_factory",
                return_value=NullAuditLogWriter(),
            ),
            patch.object(
                service_factory,
                "create_pre_tool_use_service",
                return_value=stub_service,
            ),
        ):
            try:
                exit_code = handle_pre_tool_use()
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1

        return exit_code, captured_stdout.getvalue()

    def test_codex_pretooluse_payload_accepted_by_des_adapter(self):
        """
        GIVEN: A Codex-shaped PreToolUse payload (no transcript_path field)
        WHEN: The DES adapter's handle_pre_tool_use() processes it
        THEN: The adapter returns exit code 0 (allow) without raising or crashing.
              The missing transcript_path field does NOT cause a parse error.

        Codex payload shape (per research 2026-05-05):
          {"hook_event_name": "PreToolUse", "tool_name": "Bash",
           "tool_input": {"command": "echo hello"}, "session_id": "abc123"}

        vs Claude Code which also includes:
          "transcript_path": "/path/to/transcript.jsonl"
        """
        # bypass: single-property assertion on exit_code
        codex_payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
            "session_id": "codex-session-abc123",
            # NOTE: transcript_path deliberately absent (Codex doesn't send it)
        }

        exit_code, stdout_text = self._invoke_pre_tool_use_handler(codex_payload)

        assert exit_code == 0, (
            f"DES adapter must allow Codex-shaped PreToolUse payload; "
            f"got exit_code={exit_code}, stdout={stdout_text!r}"
        )

    def test_claude_code_pretooluse_payload_still_accepted(self):
        """
        GIVEN: A Claude Code-shaped PreToolUse payload (with transcript_path)
        WHEN: The DES adapter's handle_pre_tool_use() processes it
        THEN: The adapter returns exit code 0 (allow) — regression guard.
        """
        # bypass: single-property assertion on exit_code
        claude_code_payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
            "session_id": "claude-session-xyz",
            "transcript_path": "/home/user/.claude/projects/proj/transcript.jsonl",
        }

        exit_code, _stdout = self._invoke_pre_tool_use_handler(claude_code_payload)

        assert exit_code == 0, (
            "Claude Code PreToolUse payload must still be accepted after Codex work"
        )
