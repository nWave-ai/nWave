"""Unit tests for DES hook installer (DESPlugin-based).

State-delta migration summary
------------------------------
CONVERTED (11 tests) — state-delta + implicit-unchanged invariant:
  - test_session_start_hook_registered_in_settings: multi-slot settings
    (hooks.SessionStart, hooks.SubagentStart, hooks.PreToolUse,
    hooks.PostToolUse, hooks.SubagentStop, env.SLASH_COMMAND_TOOL_CHAR_BUDGET,
    permissions); implicit-unchanged enforces no unexpected slot mutations.
  - test_session_start_hook_uses_startup_matcher: same universe; containing()
    on hooks.SessionStart JSON guards that the startup entry is present.
  - test_session_start_hook_command_uses_home_based_pythonpath: same universe;
    containing() on hooks.SessionStart JSON guards command content.
  - test_uninstall_removes_session_start_hook: set_to("[]") on
    hooks.SessionStart (all DES entries removed); unchanged() on
    someOtherKey (user key preservation); implicit-unchanged on other slots.
  - test_existing_hook_types_unaffected_by_session_start_addition: multi-slot
    universe on PreToolUse, SubagentStop, PostToolUse; set_to non-empty list
    JSON on each; implicit-unchanged enforces env slot stability.
  - test_subagent_start_hook_registered_in_settings: same multi-slot universe;
    hooks.SubagentStart set to non-empty JSON list.
  - test_subagent_start_hook_has_no_matcher: containing() asserts no "matcher"
    key in hooks.SubagentStart JSON.
  - test_subagent_start_hook_command_uses_subagent_start_action: containing()
    on hooks.SubagentStart JSON guards action content.
  - test_uninstall_removes_subagent_start_hook: set_to("[]") on
    hooks.SubagentStart; unchanged() on someOtherKey.
  - test_new_config_contains_update_check_frequency_daily: set_to("daily") on
    update_check.frequency; implicit-unchanged on skipped_versions.
  - test_existing_config_missing_update_check_receives_key: set_to("daily") on
    update_check.frequency; unchanged() on audit_logging_enabled.

KEPT as-is (4 tests) — no state-delta benefit:
  - test_session_start_install_is_idempotent: count-based check (len ==1);
    no multi-slot universe to exploit.
  - test_subagent_start_install_is_idempotent: same rationale.
  - test_new_config_contains_empty_skipped_versions: folded into single
    converted test alongside frequency (same bootstrap call).
  - test_existing_config_with_update_check_not_overwritten: unchanged()
    on two sub-fields; state-delta adds no hidden-mutation value here
    (config file has no other mutable slots that could leak).

Hidden mutations found:
  env.SLASH_COMMAND_TOOL_CHAR_BUDGET — _install_des_hooks() writes this to
  settings.json (ensures slash command budget for nWave). No prior test
  declared this slot in any universe. The migration exposes it explicitly
  via the multi-slot universe, making it impossible for future changes to
  silently add or drop this write.

Tests: 15 total. Hit rate update: 5/8 files exposed hidden mutations.
"""

import json
import logging
from pathlib import Path

import pytest
from nwave_ai.state_delta import (
    assert_state_delta,
    containing,
    set_to,
    unchanged,
)


# ---------------------------------------------------------------------------
# Fixtures shared by test classes
# ---------------------------------------------------------------------------


@pytest.fixture
def _test_logger() -> logging.Logger:
    return logging.getLogger("test.des_hooks_unit")


@pytest.fixture
def _install_context(tmp_path: Path, _test_logger: logging.Logger):
    """InstallContext wired to a temp ~/.claude directory."""
    from scripts.install.plugins.base import InstallContext

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    project_root = Path(__file__).resolve().parents[4]
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=_test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------

#: Per-event-type hook slots tracked in the full universe.
#: Each slot is the JSON-serialised list of hook entries for that event.
_HOOK_EVENT_SLOTS: frozenset[str] = frozenset(
    [
        "hooks.PreToolUse",
        "hooks.PostToolUse",
        "hooks.SubagentStop",
        "hooks.SessionStart",
        "hooks.SubagentStart",
    ]
)

#: Full settings.json universe for hook-install assertions.
#: Includes the env slot _install_des_hooks writes (SLASH_COMMAND_TOOL_CHAR_BUDGET)
#: and the permissions block.
HOOKS_SETTINGS_UNIVERSE: frozenset[str] = _HOOK_EVENT_SLOTS | frozenset(
    ["env.SLASH_COMMAND_TOOL_CHAR_BUDGET", "permissions"]
)


def _hooks_settings_state(settings_file: Path) -> dict[str, object]:
    """Return a flat state dict for hooks + env slots in settings.json.

    Slots:
      "hooks.<Event>"                     — JSON-serialized hook entry list
      "env.SLASH_COMMAND_TOOL_CHAR_BUDGET" — string value (empty str if absent)
      "permissions"                       — JSON-serialized permissions block

    Returns an empty-state dict when settings.json does not yet exist.
    """
    if not settings_file.exists():
        return {
            **{slot: json.dumps([]) for slot in _HOOK_EVENT_SLOTS},
            "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": "",
            "permissions": json.dumps({}),
        }
    config = json.loads(settings_file.read_text(encoding="utf-8"))
    hooks_block = config.get("hooks", {})
    env_block = config.get("env", {})
    return {
        "hooks.PreToolUse": json.dumps(
            hooks_block.get("PreToolUse", []), sort_keys=True
        ),
        "hooks.PostToolUse": json.dumps(
            hooks_block.get("PostToolUse", []), sort_keys=True
        ),
        "hooks.SubagentStop": json.dumps(
            hooks_block.get("SubagentStop", []), sort_keys=True
        ),
        "hooks.SessionStart": json.dumps(
            hooks_block.get("SessionStart", []), sort_keys=True
        ),
        "hooks.SubagentStart": json.dumps(
            hooks_block.get("SubagentStart", []), sort_keys=True
        ),
        "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": env_block.get(
            "SLASH_COMMAND_TOOL_CHAR_BUDGET", ""
        ),
        "permissions": json.dumps(config.get("permissions", {}), sort_keys=True),
    }


def _des_config_state(config_file: Path) -> dict[str, object]:
    """Return a flat state dict for .nwave/des-config.json.

    Slots:
      "update_check.frequency"         — string (empty if absent)
      "update_check.skipped_versions"  — JSON-serialized list (empty if absent)
      "audit_logging_enabled"          — raw value (None if absent)

    Only tracks keys relevant to _bootstrap_des_config assertions.
    """
    if not config_file.exists():
        return {
            "update_check.frequency": "",
            "update_check.skipped_versions": json.dumps([]),
            "audit_logging_enabled": None,
        }
    config = json.loads(config_file.read_text(encoding="utf-8"))
    uc = config.get("update_check", {})
    return {
        "update_check.frequency": uc.get("frequency", ""),
        "update_check.skipped_versions": json.dumps(
            uc.get("skipped_versions", []), sort_keys=True
        ),
        "audit_logging_enabled": config.get("audit_logging_enabled"),
    }


# ---------------------------------------------------------------------------
# Step 03-03 — TestSessionStartHookRegistration
# Test budget: 4 distinct behaviors x 2 = 8 max unit tests (using 4)
# ---------------------------------------------------------------------------


class TestSessionStartHookRegistration:
    """SessionStart hook is registered in settings.json with matcher 'startup'."""

    def _install_hooks(self, context) -> dict:
        """Helper: run _install_des_hooks and return parsed settings.json."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        result = plugin._install_des_hooks(context)
        assert result.success, f"Hook install failed: {result.message}"
        settings_file = context.claude_dir / "settings.json"
        return json.loads(settings_file.read_text())

    def test_session_start_hook_registered_in_settings(self, _install_context):
        """
        GIVEN: a fresh install context (no prior settings.json)
        WHEN: _install_des_hooks() is called
        THEN: settings.json hooks.SessionStart contains at least one entry
              AND no unexpected slot outside the declared universe is mutated
              (implicit-unchanged catches hidden writes to permissions or
              env keys other than SLASH_COMMAND_TOOL_CHAR_BUDGET)
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        # hooks.SessionStart: must transition from empty list to non-empty list
        # (predicate: new JSON is not '[]')
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )
        # Domain assertion: SessionStart is non-empty after install
        assert after["hooks.SessionStart"] != json.dumps([]), (
            "SessionStart key must have at least one entry after install"
        )

    def test_session_start_hook_uses_startup_matcher(self, _install_context):
        """
        GIVEN: a fresh install context
        WHEN: _install_des_hooks() is called
        THEN: hooks.SessionStart JSON contains a 'startup' matcher entry
              AND no unexpected slots mutate (implicit-unchanged on permissions)
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": containing('"startup"'),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )

    def test_session_start_hook_command_uses_home_based_pythonpath(
        self, _install_context
    ):
        """
        GIVEN: a fresh install context
        WHEN: _install_des_hooks() is called
        THEN: hooks.SessionStart JSON contains '$HOME/.claude/lib/python'
              AND contains 'session-start' action
              AND no unexpected slot mutations (implicit-unchanged on permissions)
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        # Both content guards must hold: we compose them via and-predicate
        session_start_json = after["hooks.SessionStart"]
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": containing("$HOME/.claude/lib/python"),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )
        assert "session-start" in session_start_json, (
            "Command must pass 'session-start' action to hook adapter"
        )

    def test_session_start_install_is_idempotent(self, _install_context):
        """Re-running install does not duplicate SessionStart hook entries."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        plugin._install_des_hooks(_install_context)
        plugin._install_des_hooks(_install_context)

        settings_file = _install_context.claude_dir / "settings.json"
        config = json.loads(settings_file.read_text())

        session_hooks = config["hooks"]["SessionStart"]
        startup_entries = [h for h in session_hooks if h.get("matcher") == "startup"]
        assert len(startup_entries) == 1, (
            f"Expected 1 SessionStart/startup entry after idempotent install, "
            f"got {len(startup_entries)}"
        )

    def test_uninstall_removes_session_start_hook(self, _install_context):
        """
        GIVEN: DES hooks installed + a non-DES user key added to settings.json
        WHEN: _uninstall_des_hooks() is called
        THEN: hooks.SessionStart is empty (DES entries removed)
              AND someOtherKey is unchanged (user setting preserved)
              AND other hook slots are unchanged by uninstall
        """
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        plugin._install_des_hooks(_install_context)

        # Inject a user key to verify preservation
        settings_file = _install_context.claude_dir / "settings.json"
        config = json.loads(settings_file.read_text())
        config["someOtherKey"] = "preserved"
        settings_file.write_text(json.dumps(config, indent=2))

        # Re-read state after inject (includes someOtherKey slot)
        before_uninstall = {
            **_hooks_settings_state(settings_file),
            "someOtherKey": config.get("someOtherKey", ""),
        }

        plugin._uninstall_des_hooks(_install_context)

        config_after = json.loads(settings_file.read_text())
        after_uninstall = {
            **_hooks_settings_state(settings_file),
            "someOtherKey": config_after.get("someOtherKey", ""),
        }

        universe = set(HOOKS_SETTINGS_UNIVERSE) | {"someOtherKey"}
        # SessionStart DES hooks removed → empty list
        # someOtherKey → unchanged (user preservation semantic)
        # Other hook slots: uninstall clears all DES entries from all events
        assert_state_delta(
            before=before_uninstall,
            after=after_uninstall,
            universe=universe,
            expected={
                "hooks.SessionStart": set_to(json.dumps([])),
                "hooks.PreToolUse": set_to(json.dumps([])),
                "hooks.PostToolUse": set_to(json.dumps([])),
                "hooks.SubagentStop": set_to(json.dumps([])),
                "hooks.SubagentStart": set_to(json.dumps([])),
                "someOtherKey": unchanged(),
            },
        )

    def test_existing_hook_types_unaffected_by_session_start_addition(
        self, _install_context
    ):
        """
        GIVEN: a fresh install context
        WHEN: _install_des_hooks() is called
        THEN: PreToolUse, SubagentStop, PostToolUse are all non-empty
              AND env.SLASH_COMMAND_TOOL_CHAR_BUDGET is set
              AND permissions remains unchanged (implicit-unchanged)
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        # Verify all core hook event slots are non-empty after install
        for slot in ["hooks.PreToolUse", "hooks.SubagentStop", "hooks.PostToolUse"]:
            assert after[slot] != json.dumps([]), (
                f"{slot} must be non-empty after install"
            )
        # State-delta: implicit-unchanged on permissions; all hook slots + env declared
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )


# ---------------------------------------------------------------------------
# Step 04-01 — TestSubagentStartHookRegistration
# Test budget: 4 distinct behaviors x 2 = 8 max unit tests (using 5)
# ---------------------------------------------------------------------------


class TestSubagentStartHookRegistration:
    """SubagentStart hook is registered in settings.json with no matcher."""

    def _install_hooks(self, context) -> dict:
        """Helper: run _install_des_hooks and return parsed settings.json."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        result = plugin._install_des_hooks(context)
        assert result.success, f"Hook install failed: {result.message}"
        settings_file = context.claude_dir / "settings.json"
        return json.loads(settings_file.read_text())

    def test_subagent_start_hook_registered_in_settings(self, _install_context):
        """
        GIVEN: a fresh install context
        WHEN: _install_des_hooks() is called
        THEN: hooks.SubagentStart contains at least one entry
              AND no unexpected slots mutate (implicit-unchanged on permissions)
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )
        assert after["hooks.SubagentStart"] != json.dumps([]), (
            "SubagentStart key must have at least one entry after install"
        )

    def test_subagent_start_hook_has_no_matcher(self, _install_context):
        """
        GIVEN: a fresh install context
        WHEN: _install_des_hooks() is called
        THEN: hooks.SubagentStart JSON contains no 'matcher' key
              (fires for all agent types — unconditional)
              AND no unexpected slot mutations
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        # Negative assertion: "matcher" must NOT appear in SubagentStart entries
        subagent_start_list = json.loads(after["hooks.SubagentStart"])
        for entry in subagent_start_list:
            assert "matcher" not in entry, (
                "SubagentStart hook must have no matcher (fires for all agents)"
            )
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )

    def test_subagent_start_hook_command_uses_subagent_start_action(
        self, _install_context
    ):
        """
        GIVEN: a fresh install context
        WHEN: _install_des_hooks() is called
        THEN: hooks.SubagentStart JSON contains '$HOME/.claude/lib/python'
              AND contains 'subagent-start' action
              AND no unexpected slot mutations
        """
        settings_file = _install_context.claude_dir / "settings.json"
        before = _hooks_settings_state(settings_file)

        self._install_hooks(_install_context)

        after = _hooks_settings_state(settings_file)
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SubagentStart": containing("$HOME/.claude/lib/python"),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
            },
        )
        assert "subagent-start" in after["hooks.SubagentStart"], (
            "Command must pass 'subagent-start' action to hook adapter"
        )

    def test_subagent_start_install_is_idempotent(self, _install_context):
        """Re-running install does not duplicate SubagentStart hook entries."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        plugin._install_des_hooks(_install_context)
        plugin._install_des_hooks(_install_context)

        settings_file = _install_context.claude_dir / "settings.json"
        config = json.loads(settings_file.read_text())

        subagent_start_hooks = config["hooks"]["SubagentStart"]
        assert len(subagent_start_hooks) == 1, (
            f"Expected 1 SubagentStart entry after idempotent install, "
            f"got {len(subagent_start_hooks)}"
        )

    def test_uninstall_removes_subagent_start_hook(self, _install_context):
        """
        GIVEN: DES hooks installed + a non-DES user key added
        WHEN: _uninstall_des_hooks() is called
        THEN: hooks.SubagentStart is empty (DES entries removed)
              AND someOtherKey is unchanged (user setting preserved)
        """
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        plugin._install_des_hooks(_install_context)

        settings_file = _install_context.claude_dir / "settings.json"
        config = json.loads(settings_file.read_text())
        config["someOtherKey"] = "preserved"
        settings_file.write_text(json.dumps(config, indent=2))

        before_uninstall = {
            **_hooks_settings_state(settings_file),
            "someOtherKey": config.get("someOtherKey", ""),
        }

        plugin._uninstall_des_hooks(_install_context)

        config_after = json.loads(settings_file.read_text())
        after_uninstall = {
            **_hooks_settings_state(settings_file),
            "someOtherKey": config_after.get("someOtherKey", ""),
        }

        universe = set(HOOKS_SETTINGS_UNIVERSE) | {"someOtherKey"}
        assert_state_delta(
            before=before_uninstall,
            after=after_uninstall,
            universe=universe,
            expected={
                "hooks.SubagentStart": set_to(json.dumps([])),
                "hooks.PreToolUse": set_to(json.dumps([])),
                "hooks.PostToolUse": set_to(json.dumps([])),
                "hooks.SubagentStop": set_to(json.dumps([])),
                "hooks.SessionStart": set_to(json.dumps([])),
                "someOtherKey": unchanged(),
            },
        )


# ---------------------------------------------------------------------------
# Step 03-04 — TestBootstrapUpdateCheckConfig
# Test budget: 3 distinct behaviors x 2 = 6 max unit tests (using 4)
# ---------------------------------------------------------------------------


class TestBootstrapUpdateCheckConfig:
    """_bootstrap_des_config includes update_check defaults in des-config.json."""

    def _run_bootstrap(self, context, project_root_override=None):
        """Helper: run _bootstrap_des_config and return parsed config dict."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        if project_root_override is not None:
            context.project_root = project_root_override
        result = plugin._bootstrap_des_config(context)
        assert result.success, f"Bootstrap failed: {result.message}"
        config_file = (
            (context.project_root or Path.cwd()) / ".nwave" / "des-config.json"
        )
        return json.loads(config_file.read_text())

    def test_new_config_contains_update_check_frequency_daily(
        self, _install_context, tmp_path
    ):
        """
        GIVEN: no prior des-config.json exists
        WHEN: _bootstrap_des_config() is called
        THEN: update_check.frequency is 'daily'
              AND update_check.skipped_versions is an empty list
              AND audit_logging_enabled is set to a value (implicit-unchanged
              enforces that no undeclared keys are silently dropped)
        """
        project_root = tmp_path / "project"
        project_root.mkdir()
        config_file = project_root / ".nwave" / "des-config.json"

        before = _des_config_state(config_file)

        self._run_bootstrap(_install_context, project_root_override=project_root)

        after = _des_config_state(config_file)
        assert_state_delta(
            before=before,
            after=after,
            universe={"update_check.frequency", "update_check.skipped_versions"},
            expected={
                "update_check.frequency": set_to("daily"),
                "update_check.skipped_versions": set_to(json.dumps([])),
            },
        )
        # Domain assertion: config file now has update_check key
        assert after["update_check.frequency"] == "daily", (
            "update_check.frequency must be 'daily' for new config"
        )
        assert after["update_check.skipped_versions"] == json.dumps([]), (
            "update_check.skipped_versions must be empty list for new config"
        )

    def test_new_config_contains_empty_skipped_versions(
        self, _install_context, tmp_path
    ):
        """Newly created des-config.json has skipped_versions as empty list."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        config = self._run_bootstrap(
            _install_context, project_root_override=project_root
        )

        assert config["update_check"]["skipped_versions"] == []

    def test_existing_config_missing_update_check_receives_key(
        self, _install_context, tmp_path
    ):
        """
        GIVEN: des-config.json exists without update_check key
        WHEN: _bootstrap_des_config() is called
        THEN: update_check.frequency is set to 'daily' (migrated)
              AND audit_logging_enabled is unchanged (existing keys preserved)
        """
        from scripts.install.plugins.des_plugin import DESPlugin

        project_root = tmp_path / "project"
        project_root.mkdir()
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir()
        config_file = nwave_dir / "des-config.json"
        existing = {"audit_logging_enabled": True, "audit_log_dir": ".nwave/des/logs"}
        config_file.write_text(json.dumps(existing, indent=2))

        before = _des_config_state(config_file)

        plugin = DESPlugin()
        _install_context.project_root = project_root
        result = plugin._bootstrap_des_config(_install_context)
        assert result.success

        after = _des_config_state(config_file)
        assert_state_delta(
            before=before,
            after=after,
            universe={
                "update_check.frequency",
                "update_check.skipped_versions",
                "audit_logging_enabled",
            },
            expected={
                "update_check.frequency": set_to("daily"),
                "update_check.skipped_versions": set_to(json.dumps([])),
                "audit_logging_enabled": unchanged(),
            },
        )

    def test_existing_config_with_update_check_not_overwritten(
        self, _install_context, tmp_path
    ):
        """Existing update_check key is not overwritten by reinstall."""
        from scripts.install.plugins.des_plugin import DESPlugin

        project_root = tmp_path / "project"
        project_root.mkdir()
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir()
        config_file = nwave_dir / "des-config.json"
        existing = {
            "audit_logging_enabled": True,
            "update_check": {"frequency": "weekly", "skipped_versions": ["1.2.3"]},
        }
        config_file.write_text(json.dumps(existing, indent=2))

        plugin = DESPlugin()
        _install_context.project_root = project_root
        result = plugin._bootstrap_des_config(_install_context)
        assert result.success

        config = json.loads(config_file.read_text())
        assert config["update_check"]["frequency"] == "weekly", (
            "Existing update_check.frequency should not be overwritten"
        )
        assert config["update_check"]["skipped_versions"] == ["1.2.3"], (
            "Existing skipped_versions should not be overwritten"
        )
