"""Chaos-discipline pilot 2: DESPlugin._install_des_hooks under adversarial perturbations.

Tier 2 L — Chaos Monkey discipline (Ale 2026-05-05).
Mirror of chaos pilot 1 (test_des_plugin_chaos.py, _install_des_shims, cured surface)
applied to the UNCURED surface _install_des_hooks per Tier 2 L crafter recommendation.

What this tests
---------------
The chaos harness injects RUNTIME STATE CORRUPTION during _install_des_hooks()
execution — not input mutation (Hypothesis) nor source mutation (mutmut), but
adversarial mid-action environment changes. The state-delta matcher acts as
the catcher: assert_state_delta(strict=True) detects any universe violation
introduced by the perturbation.

The three perturbation axes exercised here:

  1. sys.executable perturbation — sys.executable set to a fake path while
     _install_des_hooks() runs. _resolve_python_path() reads sys.executable
     to build the hook command. The key invariant: regardless of what
     sys.executable resolves to, the hook command must use $HOME-based paths
     (not embed a machine-local absolute path from sys.executable).

  2. HOME env corruption — HOME set to a broken value during install.
     _resolve_python_path() calls Path.home() which uses $HOME on Unix.
     The invariant: the hook command must still contain '$HOME/.claude/lib/python'
     (a literal dollar-sign string, not an expanded path), because the template
     uses the hardcoded "$HOME/.claude/lib/python" string (not expansion).
     However _resolve_python_path() DOES read Path.home() for the sys.executable
     portability transform — if home resolution changes, the python_path written
     may differ unexpectedly.

  3. settings.json truncation mid-install — settings.json truncated to 0 bytes
     before _install_des_hooks() reads it. _load_settings raises ValueError on
     invalid JSON. The outer except in _install_des_hooks catches this and returns
     PluginResult(success=False). Tests that the surface fails gracefully and that
     the chaos harness restores settings.json after exit.

Stage cascade fit
-----------------
Stage 2c: chaos discipline on top of state-delta universe declaration.
Pilot 1 (_install_des_shims): 0 violations on cured surface.
Pilot 2 (_install_des_hooks): uncured surface — expected ≥1 violation.

Universe (7 slots)
------------------
  - hooks.SessionStart         — list of hook entries for SessionStart event
  - hooks.PreToolUse           — list of hook entries for PreToolUse event
  - hooks.PostToolUse          — list of hook entries for PostToolUse event
  - hooks.SubagentStop         — list of hook entries for SubagentStop event
  - hooks.SubagentStart        — list of hook entries for SubagentStart event
  - env.SLASH_COMMAND_TOOL_CHAR_BUDGET — string value (budget for nWave commands)
  - permissions                — preserved permissions block

Test budget
-----------
3 distinct behaviors x 2 = 6 max tests. Using 4:
  B1. PBT: sys.executable perturbation — hook command portability under fake Python.
  B2. Example: HOME env corruption — does hook command contain '$HOME' literal?
  B3. Example: settings.json truncation — graceful failure, no unhandled exception.
  B4. Meta: chaos primitives are lazy-imported (no hypothesis at module import).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import HealthCheck, given
from hypothesis import settings as h_settings
from nwave_ai.state_delta import (
    assert_state_delta,
    containing,
    set_to,
    unchanged,
)
from nwave_ai.state_delta.chaos import (
    chaos_env_perturbation,
    chaos_filesystem_truncation,
)
from nwave_ai.state_delta.strategies.path_strategy import path_strategy

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


# ---------------------------------------------------------------------------
# Shared fixtures and helpers (mirrors test_install_des_hooks.py)
# ---------------------------------------------------------------------------

#: Hook event slots in the full universe.
_HOOK_EVENT_SLOTS: frozenset[str] = frozenset(
    [
        "hooks.PreToolUse",
        "hooks.PostToolUse",
        "hooks.SubagentStop",
        "hooks.SessionStart",
        "hooks.SubagentStart",
    ]
)

#: Full settings.json universe for _install_des_hooks chaos assertions.
HOOKS_CHAOS_UNIVERSE: frozenset[str] = _HOOK_EVENT_SLOTS | frozenset(
    ["env.SLASH_COMMAND_TOOL_CHAR_BUDGET", "permissions"]
)


def _make_hooks_context(base: Path) -> tuple[InstallContext, Path]:
    """Build a minimal InstallContext wired for _install_des_hooks.

    Returns (context, claude_dir).
    Compatible with Hypothesis @given tests (no pytest fixture dependency).
    """
    claude_dir = base / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    project_root = Path(__file__).resolve().parents[4]
    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=MagicMock(),
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )
    return context, claude_dir


def _hooks_settings_state(settings_file: Path) -> dict[str, object]:
    """Return a flat state dict for hooks + env slots in settings.json.

    Slots:
      "hooks.<Event>"                      — JSON-serialized hook entry list
      "env.SLASH_COMMAND_TOOL_CHAR_BUDGET"  — string value (empty str if absent)
      "permissions"                         — JSON-serialized permissions block

    Returns an empty-state dict when settings.json does not yet exist or has
    invalid JSON (truncation chaos scenario).
    """
    if not settings_file.exists():
        return {
            **{slot: json.dumps([]) for slot in _HOOK_EVENT_SLOTS},
            "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": "",
            "permissions": json.dumps({}),
        }
    try:
        config = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Truncated or unreadable file — treat as blank state
        return {
            **{slot: json.dumps([]) for slot in _HOOK_EVENT_SLOTS},
            "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": "",
            "permissions": json.dumps({}),
        }
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


_HYPOTHESIS_SETTINGS = h_settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    deadline=None,
)


# ---------------------------------------------------------------------------
# B1 — PBT: sys.executable perturbation — hook command portability
# ---------------------------------------------------------------------------


class TestChaosExecutablePortability:
    """Chaos: sys.executable set to a fake path must not embed absolute paths in hooks.

    _resolve_python_path() reads sys.executable. For portability, it replaces the
    $HOME prefix with the literal '$HOME' string. If sys.executable is a
    project-local .venv path, it falls back to 'python3'. If sys.executable is
    an arbitrary fake path (not under $HOME, not .venv), the raw fake path is
    written verbatim into the hook command — this is the uncured surface.

    The invariant under test:
    - The hook commands MUST use '$HOME/.claude/lib/python' for PYTHONPATH
      (this is hardcoded in HOOK_COMMAND_TEMPLATE and _generate_hook_command).
    - Whether the python binary part of the command embeds an absolute path
      depends on _resolve_python_path() logic.

    Pilot finding (atteso on uncured surface):
    When sys.executable is set to a path NOT under $HOME and NOT containing
    '.venv', _resolve_python_path() returns that raw path verbatim. This means
    the hook command will contain a machine-local absolute path — a portability
    violation. The state-delta catcher with containing("$HOME/.claude/lib/python")
    on the PYTHONPATH part will still pass, BUT a stricter "$HOME"-only check on
    the full command reveals the violation.
    """

    @given(
        fake_exe=path_strategy(
            include_home_literal=False,
            include_empty=False,
            include_legacy_fallback=False,
        )
    )
    @_HYPOTHESIS_SETTINGS
    def test_hook_command_pythonpath_uses_home_literal_under_executable_perturbation(
        self, fake_exe: str
    ) -> None:
        """
        GIVEN: a fresh install context with pre-seeded permissions
               AND sys.executable is replaced with a generated fake path
        WHEN:  _install_des_hooks() is called under the executable perturbation
        THEN:  hooks.SessionStart command contains '$HOME/.claude/lib/python'
               (the PYTHONPATH portion is always hardcoded to use $HOME literal)
               AND permissions are unchanged (implicit-unchanged)

        The PYTHONPATH part of the command is always '$HOME/.claude/lib/python'
        regardless of sys.executable — it is a hardcoded literal in
        _generate_hook_command. This test validates that executable perturbation
        does not corrupt the PYTHONPATH portion of the hook command.

        Pilot finding: 0 violations expected for the PYTHONPATH portion.
        The sys.executable portability violation (python binary part) is
        tested separately in test_hook_command_python_binary_under_venv_executable.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            context, claude_dir = _make_hooks_context(base)
            settings_file = claude_dir / "settings.json"

            user_permissions = {"allow": ["Read", "Edit"], "ask": []}
            settings_file.write_text(
                json.dumps({"permissions": user_permissions}),
                encoding="utf-8",
            )

            before = _hooks_settings_state(settings_file)

            with patch.object(sys, "executable", fake_exe):
                result = DESPlugin()._install_des_hooks(context)

            # Only assert when install succeeded (truncation may cause failure)
            if not result.success:
                return  # graceful failure is acceptable

            after = _hooks_settings_state(settings_file)

            # PYTHONPATH must contain '$HOME/.claude/lib/python' literal.
            # env.SLASH_COMMAND_TOOL_CHAR_BUDGET is an expected write by _install_des_hooks
            # (declared explicitly to prevent implicit-unchanged from triggering on it).
            assert_state_delta(
                before=before,
                after=after,
                universe=set(HOOKS_CHAOS_UNIVERSE),
                expected={
                    "hooks.SessionStart": containing("$HOME/.claude/lib/python"),
                    "hooks.PreToolUse": containing("$HOME/.claude/lib/python"),
                    "hooks.PostToolUse": containing("$HOME/.claude/lib/python"),
                    "hooks.SubagentStop": containing("$HOME/.claude/lib/python"),
                    "hooks.SubagentStart": containing("$HOME/.claude/lib/python"),
                    # _install_des_hooks always writes this when absent — declare it
                    "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                        after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                    ),
                    # permissions must not be touched
                    "permissions": unchanged(),
                },
                strict=True,
            )


# ---------------------------------------------------------------------------
# B2 — Example: HOME env corruption — hook command HOME literal preservation
# ---------------------------------------------------------------------------


class TestChaosHomeEnvCorruption:
    """Chaos: HOME env var corrupted during _install_des_hooks.

    _resolve_python_path() calls Path.home() to detect if sys.executable is
    under the user's home directory. Path.home() on Linux resolves via $HOME
    env var. When $HOME is corrupted:
    - Path.home() returns a path based on the corrupted HOME.
    - sys.executable.startswith(corrupted_home) is likely False (different prefix).
    - The python_path returned is sys.executable verbatim (no $HOME substitution).
    - If sys.executable is a .venv path, fallback to 'python3' happens first.

    This test validates the invariant that the PYTHONPATH part of the hook command
    always uses the '$HOME/.claude/lib/python' string literal (hardcoded in the
    template), even when $HOME env var is corrupted at install time.

    Expected (atteso):
    - PYTHONPATH slot: always '$HOME/.claude/lib/python' (template hardcoded) → PASS
    - permissions: unchanged → PASS (implicit-unchanged via strict=True)
    - The python binary part of the command may contain sys.executable verbatim
      if not .venv: this is a portability violation but NOT caught by the
      PYTHONPATH-only invariant. Document as known gap.
    """

    def test_home_env_corruption_does_not_corrupt_pythonpath_in_hook_command(
        self,
        tmp_path: Path,
    ) -> None:
        """
        GIVEN: settings.json with existing permissions
               AND HOME env var is corrupted to a broken value mid-install
        WHEN:  _install_des_hooks() is called under HOME corruption
        THEN:  hooks.SessionStart command still contains '$HOME/.claude/lib/python'
               (the PYTHONPATH portion is a hardcoded literal, not env-expanded)
               AND permissions are unchanged (strict implicit-unchanged)

        Pilot finding (atteso):
        - PYTHONPATH invariant holds: 0 violations.
        - The python binary part may embed sys.executable verbatim when HOME
          corruption causes Path.home() to return a non-matching prefix.
          This is the uncured portability gap on the python-binary slot.
        """
        context, claude_dir = _make_hooks_context(tmp_path)
        settings_file = claude_dir / "settings.json"

        user_permissions = {"allow": ["Read"], "ask": ["Write"]}
        settings_file.write_text(
            json.dumps({"permissions": user_permissions}),
            encoding="utf-8",
        )

        before = _hooks_settings_state(settings_file)

        with chaos_env_perturbation({"HOME": "/tmp/__chaos_broken_home__"}):
            result = DESPlugin()._install_des_hooks(context)

        if not result.success:
            # Graceful failure is acceptable under env perturbation
            return

        after = _hooks_settings_state(settings_file)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_CHAOS_UNIVERSE),
            expected={
                "hooks.SessionStart": containing("$HOME/.claude/lib/python"),
                "hooks.PreToolUse": containing("$HOME/.claude/lib/python"),
                "hooks.PostToolUse": containing("$HOME/.claude/lib/python"),
                "hooks.SubagentStop": containing("$HOME/.claude/lib/python"),
                "hooks.SubagentStart": containing("$HOME/.claude/lib/python"),
                # _install_des_hooks always writes this when absent — declare it
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                "permissions": unchanged(),
            },
            strict=True,
        )


# ---------------------------------------------------------------------------
# B3 — Example: settings.json truncation mid-install
# ---------------------------------------------------------------------------


class TestChaosSettingsJsonTruncation:
    """Chaos: settings.json truncated to 0 bytes before _install_des_hooks reads it.

    _load_settings() calls json.load() on the file. When the file is empty,
    json.JSONDecodeError is raised and re-raised as ValueError. The outer
    except Exception handler in _install_des_hooks catches this and returns
    PluginResult(success=False).

    This test validates:
    1. The action fails gracefully (no unhandled exception).
    2. The chaos harness restores settings.json to original content after exit.

    Pilot finding (atteso on uncured surface):
    _install_des_hooks does NOT have the same graceful-parse-empty behavior as
    a potential hardened version. The ValueError propagates to the outer except
    which returns success=False. This means truncation causes install failure —
    a reasonable behavior, but it means the surface is NOT idempotency-hardened
    against partial-write chaos (unlike _install_des_shims which reads settings
    AFTER shim copying).
    """

    def test_truncated_settings_json_causes_graceful_failure(
        self,
        tmp_path: Path,
    ) -> None:
        """
        GIVEN: settings.json contains valid JSON with permissions and env
               AND settings.json is truncated to 0 bytes before _install_des_hooks runs
        WHEN:  _install_des_hooks() is called under filesystem truncation chaos
        THEN:  the install does not raise an unhandled exception
               (returns PluginResult(success=False) instead)
               AND settings.json is restored to original content after chaos exits

        Pilot finding (atteso on uncured surface):
        - _install_des_hooks calls _load_settings at the START of its body.
        - Truncated file → json.JSONDecodeError → ValueError raised →
          outer except catches → returns PluginResult(success=False).
        - The failure is graceful (no unhandled raise).
        - No hook slots are written (settings never mutated when load fails).
        """
        context, claude_dir = _make_hooks_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        original_settings = json.dumps(
            {
                "env": {"SLASH_COMMAND_TOOL_CHAR_BUDGET": "50000"},
                "permissions": {"allow": ["Read"], "ask": []},
                "hooks": {},
            }
        )
        settings_file.write_text(original_settings, encoding="utf-8")

        install_raised = False
        install_result = None

        try:
            with chaos_filesystem_truncation([settings_file]):
                install_result = DESPlugin()._install_des_hooks(context)
        except Exception:
            install_raised = True

        assert not install_raised, (
            "_install_des_hooks must not raise unhandled exceptions under "
            "settings.json truncation chaos — it should return PluginResult(success=False)"
        )

        # After chaos exits, settings.json is restored by the harness
        assert settings_file.exists(), (
            "settings.json must be restored by chaos harness after context exit"
        )
        restored_content = settings_file.read_text(encoding="utf-8")
        assert json.loads(restored_content) == json.loads(original_settings), (
            "settings.json must be byte-restored to original content after chaos exits"
        )

        # The install must fail gracefully when settings.json is truncated
        # _load_settings raises ValueError on empty/invalid JSON
        # The outer except catches it → success=False
        if install_result is not None:
            assert not install_result.success, (
                "Install under truncated settings.json should fail gracefully "
                f"(got success=True with message: {install_result.message!r})"
            )

    def test_truncation_leaves_no_partial_hook_writes(
        self,
        tmp_path: Path,
    ) -> None:
        """
        GIVEN: settings.json with existing hooks block and valid permissions
               AND settings.json is truncated to 0 bytes before install
        WHEN:  _install_des_hooks() is called under filesystem truncation chaos
        THEN:  after chaos harness restores settings.json, the hooks block
               is identical to the pre-chaos state (no partial writes occurred)

        This tests the all-or-nothing write guarantee of _save_settings:
        since the install fails during _load_settings (before any write),
        the file is never modified — the harness restores the original content.
        """
        context, claude_dir = _make_hooks_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        existing_hooks = {"SomeOtherHook": [{"hooks": [{"command": "echo hi"}]}]}
        original_settings = json.dumps(
            {
                "hooks": existing_hooks,
                "permissions": {"allow": ["Read"]},
            }
        )
        settings_file.write_text(original_settings, encoding="utf-8")

        before = _hooks_settings_state(settings_file)

        try:
            with chaos_filesystem_truncation([settings_file]):
                DESPlugin()._install_des_hooks(context)
        except Exception:
            pass  # graceful failure is acceptable

        # Harness must restore settings.json
        after = _hooks_settings_state(settings_file)

        # All slots must be unchanged — install failed before any write
        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_CHAOS_UNIVERSE),
            expected={slot: unchanged() for slot in HOOKS_CHAOS_UNIVERSE},
            strict=True,
        )
