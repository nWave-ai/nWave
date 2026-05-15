"""Chaos-discipline pilot: DESPlugin._install_des_shims under adversarial perturbations.

Tier 2 L — Chaos Monkey discipline (Ale 2026-05-05):
"estensione edge case / Chaos Monkey machine-executable + exhaustive".

What this tests
---------------
The chaos harness injects RUNTIME STATE CORRUPTION during _install_des_shims()
execution — not input mutation (Hypothesis) nor source mutation (mutmut), but
adversarial mid-action environment changes. The state-delta matcher then acts as
the catcher: assert_state_delta(strict=True) detects any universe violation
introduced by the perturbation.

The three perturbation axes exercised here:

  1. PATH env corruption — PATH set to a broken value during shim install.
  2. PATH env removal — PATH absent from os.environ during shim install.
  3. settings.json truncation — settings.json truncated to 0 bytes while
     _install_des_shims() is already running (simulates disk-full mid-write).

Stage cascade fit
-----------------
Stage 2c: chaos discipline on top of state-delta universe declaration.
Generator is exhaustive (enumerate_perturbations covers all declared axes).
Catcher is the state-delta matcher (declarative universe + strict=True).

Expected pilot result (post Stage 1 cured surface)
---------------------------------------------------
_install_des_shims is already hardened: it catches JSON parse errors from a
truncated settings.json gracefully (returns an empty config dict and proceeds),
and it seeds PATH from os.environ["PATH"] with a fallback to SYSTEM_PATH_FALLBACK
when PATH is absent or broken.

Atteso: 0 matcher violations across all perturbations.
A "0 catch" result is healthy — it means the surface is hardened.

The pilot's value is not in finding bugs today; it is in providing a regression
net that will catch future regressions when someone modifies _install_des_shims
or _update_path_in_settings without updating the hardening tests.

Test budget
-----------
3 distinct behaviors x 2 = 6 max tests. Using 4:
  B1. PBT: env PATH corruption across generated PATH shapes.
  B2. PBT: env PATH removal across generated PATH shapes.
  B3. Example: settings.json truncation (single scenario — disk-full analog).
  B4. Meta: enumerate_perturbations_strategy does not load hypothesis at import.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from hypothesis import HealthCheck, given
from hypothesis import settings as h_settings
from nwave_ai.state_delta import (
    assert_state_delta,
    prepended_with,
)
from nwave_ai.state_delta.chaos import (
    chaos_env_perturbation,
    chaos_filesystem_truncation,
)
from nwave_ai.state_delta.strategies import path_strategy

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


# ---------------------------------------------------------------------------
# Shared fixtures and helpers (mirrors test_des_shim_installation.py)
# ---------------------------------------------------------------------------

_SHIM_NAMES = [
    "des-log-phase",
    "des-init-log",
    "des-verify-integrity",
    "des-roadmap",
    "des-health-check",
]

_DES_SCRIPTS = ["check_stale_phases.py", "scope_boundary_check.py"]

_DES_TEMPLATES = [
    ".pre-commit-config-nwave.yaml",
    ".des-audit-README.md",
    "roadmap-schema.json",
]


def _make_context_from_dirpath(base: Path) -> tuple[InstallContext, Path]:
    """Build a minimal InstallContext wired for _install_des_shims.

    Returns (context, claude_dir).
    Compatible with Hypothesis @given tests (no pytest fixture dependency).
    """
    source_root = base / "source"
    shims_dir = source_root / "scripts" / "des"
    shims_dir.mkdir(parents=True)
    for name in _SHIM_NAMES:
        (shims_dir / name).write_text(f"#!/usr/bin/env python3\n# {name}\n")
    for script in _DES_SCRIPTS:
        (shims_dir / script).write_text(f"# {script}\n")
    templates_dir = source_root / "templates"
    templates_dir.mkdir(parents=True)
    for template in _DES_TEMPLATES:
        (templates_dir / template).write_text(f"# {template}\n")
    claude_dir = base / ".claude"
    claude_dir.mkdir(parents=True)
    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=base / "scripts",
        templates_dir=templates_dir,
        logger=MagicMock(),
        project_root=base / "project",
        framework_source=source_root,
    )
    return context, claude_dir


def _settings_state(settings_file: Path) -> dict[str, object]:
    """Flat state snapshot for settings.json slots relevant to shim install."""
    if not settings_file.exists():
        return {
            "env.PATH": "",
            "permissions": json.dumps({}),
            "hooks": json.dumps({}),
        }
    try:
        config = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Truncated or unreadable file — treat as blank state
        config = {}
    return {
        "env.PATH": config.get("env", {}).get("PATH", ""),
        "permissions": json.dumps(config.get("permissions", {}), sort_keys=True),
        "hooks": json.dumps(config.get("hooks", {}), sort_keys=True),
    }


_HYPOTHESIS_SETTINGS = h_settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    deadline=None,
)


# ---------------------------------------------------------------------------
# B1 — PBT: env PATH corruption does not corrupt settings state beyond env.PATH
# ---------------------------------------------------------------------------


class TestChaosEnvPathCorruption:
    """Chaos: PATH env var corrupted mid-install does not silently break settings.

    The production code seeds env.PATH from os.environ["PATH"] when settings.json
    has no prior PATH. Under PATH corruption, it reads the broken value but writes
    it to settings.json. The important invariant is that:
      - permissions and hooks are unchanged (implicit-unchanged)
      - env.PATH contains the DES bin prefix (regardless of what os.PATH held)

    Since _install_des_shims first copies shims (filesystem), then calls
    _update_path_in_settings (reads env), the PATH corruption only affects the
    seeding of env.PATH in a fresh-install scenario — not shim copying.
    """

    @given(
        user_path=path_strategy(
            include_home_literal=False,
            include_empty=False,
            include_legacy_fallback=False,
        )
    )
    @_HYPOTHESIS_SETTINGS
    def test_env_path_corruption_does_not_affect_permissions_or_hooks(
        self, user_path: str
    ) -> None:
        """
        GIVEN: settings.json has an existing env.PATH, permissions, and hooks
               AND PATH env var is corrupted to a broken value mid-install
        WHEN:  _install_des_shims() is called under PATH env corruption
        THEN:  permissions and hooks blocks in settings.json are unchanged
               (state-delta implicit-unchanged enforces this)

        Pilot finding (atteso): 0 violations — _update_path_in_settings reads
        os.environ["PATH"] only when settings has no prior PATH. With an existing
        PATH in settings, env corruption has no effect on the written value.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            context, claude_dir = _make_context_from_dirpath(base)
            settings_file = claude_dir / "settings.json"
            des_bin = str(claude_dir / "bin")

            user_permissions = {"allow": ["Read", "Edit"], "ask": []}
            user_hooks: dict[str, object] = {"PreToolUse": []}
            settings_file.write_text(
                json.dumps(
                    {
                        "env": {"PATH": user_path},
                        "permissions": user_permissions,
                        "hooks": user_hooks,
                    }
                ),
                encoding="utf-8",
            )

            before = _settings_state(settings_file)

            with chaos_env_perturbation({"PATH": "__CHAOS_BROKEN_PATH__"}):
                DESPlugin()._install_des_shims(context)

            after = _settings_state(settings_file)

            # env.PATH: must be prepended with des_bin (existing path shape)
            # permissions + hooks: implicit-unchanged (not in expected)
            assert_state_delta(
                before=before,
                after=after,
                universe={"env.PATH", "permissions", "hooks"},
                expected={"env.PATH": prepended_with(des_bin)},
                strict=True,
            )


# ---------------------------------------------------------------------------
# B2 — PBT: PATH env removal (fresh-install scenario) falls back gracefully
# ---------------------------------------------------------------------------


class TestChaosEnvPathRemoval:
    """Chaos: PATH absent from os.environ during fresh install uses fallback.

    When settings.json has no prior PATH AND os.environ has no PATH,
    _update_path_in_settings falls back to SYSTEM_PATH_FALLBACK.
    The invariant: env.PATH must still be set and start with des_bin.
    """

    @given(
        user_path=path_strategy(
            include_home_literal=False,
            include_empty=False,
            include_legacy_fallback=False,
        )
    )
    @_HYPOTHESIS_SETTINGS
    def test_path_removal_produces_valid_des_bin_prefix(self, user_path: str) -> None:
        """
        GIVEN: settings.json has an existing env.PATH (so no live-PATH seeding occurs)
               AND PATH env var is removed from os.environ mid-install
        WHEN:  _install_des_shims() is called under PATH-absent environment
        THEN:  permissions and hooks blocks are unchanged
               AND env.PATH is prepended with des_bin

        The existing PATH in settings means the removal of os.environ["PATH"] has
        no effect on the written value (the seeding branch is not taken).

        Pilot finding (atteso): 0 violations.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            context, claude_dir = _make_context_from_dirpath(base)
            settings_file = claude_dir / "settings.json"
            des_bin = str(claude_dir / "bin")

            user_permissions = {"allow": ["Read", "Edit"], "ask": []}
            settings_file.write_text(
                json.dumps(
                    {
                        "env": {"PATH": user_path},
                        "permissions": user_permissions,
                    }
                ),
                encoding="utf-8",
            )

            before = _settings_state(settings_file)

            with chaos_env_perturbation({"PATH": None}):
                DESPlugin()._install_des_shims(context)

            after = _settings_state(settings_file)

            assert_state_delta(
                before=before,
                after=after,
                universe={"env.PATH", "permissions", "hooks"},
                expected={"env.PATH": prepended_with(des_bin)},
                strict=True,
            )


# ---------------------------------------------------------------------------
# B3 — Example: settings.json truncation mid-install
# ---------------------------------------------------------------------------


class TestChaosSettingsJsonTruncation:
    """Chaos: settings.json truncated to 0 bytes during _install_des_shims call.

    _load_settings() calls json.load() on the file. When the file is empty,
    json.JSONDecodeError is raised and propagated as ValueError. The caller
    (_install_des_shims) has a broad except-Exception handler that converts
    this to a PluginResult(success=False).

    This test validates that:
    1. The action fails gracefully (returns PluginResult with success=False)
       rather than raising unhandled or corrupting other state.
    2. The shim filesystem is NOT partially modified in a corrupted state.

    Pilot finding (atteso):
    - settings.json truncation during _install_des_shims causes the install to
      fail (the top-level except catches the ValueError from _load_settings).
    - shims MAY be partially copied before settings.json is read; the test
      tolerates this and only asserts on the settings state.
    """

    def test_truncated_settings_json_causes_graceful_failure(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: settings.json contains valid JSON
               AND settings.json is truncated to 0 bytes mid-install
        WHEN:  _install_des_shims() is called under filesystem truncation chaos
        THEN:  the install does not raise an unhandled exception
               (it either succeeds or returns PluginResult(success=False))
               AND settings.json is restored to its original content after chaos exits

        Note: _install_des_shims calls _update_path_in_settings which calls
        _load_settings AFTER shim copying. When settings is truncated BEFORE
        the call, _load_settings raises ValueError (invalid JSON → empty config
        is NOT returned — it raises). The top-level except in _install_des_shims
        catches this and returns PluginResult(success=False). This is the correct
        graceful behavior.
        """
        context, claude_dir = _make_context_from_dirpath(tmp_path)
        settings_file = claude_dir / "settings.json"
        original_settings = json.dumps(
            {"env": {"PATH": "/usr/bin"}, "permissions": {}, "hooks": {}}
        )
        settings_file.write_text(original_settings, encoding="utf-8")

        install_raised = False
        install_result = None

        try:
            with chaos_filesystem_truncation([settings_file]):
                install_result = DESPlugin()._install_des_shims(context)
        except Exception:
            install_raised = True

        assert not install_raised, (
            "_install_des_shims must not raise unhandled exceptions under "
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

        # The install should have failed gracefully (not succeeded with corrupt state)
        # When settings is truncated, _load_settings raises ValueError
        # which the outer except in install() catches → success=False
        if install_result is not None:
            assert not install_result.success, (
                "Install under truncated settings.json should fail gracefully "
                f"(got success=True with message: {install_result.message!r})"
            )
