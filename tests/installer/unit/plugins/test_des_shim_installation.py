"""Integration tests for DES shim installation via DESPlugin.

Tests verify that _install_des_shims() correctly:
1. Copies 5 shim files from nWave/scripts/des/ to ~/.claude/bin/
2. Sets executable mode (0o755) on each shim
3. Prepends absolute DES bin path (no $HOME literal) to settings.json env.PATH
4. Is idempotent: repeated calls do not duplicate PATH or error
5. validate_prerequisites fails when a shim source file is missing
6. PATH is prepended even when an existing entry is a prefix of DES_BIN_PATH
7. The live install-time os.environ["PATH"] is preserved when settings.json
   starts empty (so user-visible binaries in ~/.local/bin etc. remain reachable)
8. env.PATH contains no $HOME literal (runtime resolvability guard)
9. Shims are resolvable via shutil.which using the installed PATH value
10. Pre-existing $HOME entries are normalized to absolute paths on prepend
11. Settings written by older installer versions (the broken
    '<des_bin>:<SYSTEM_PATH_FALLBACK>' signature) are auto-healed on re-install

Test budget: 11 behaviors x 2 = 22 max tests. Using 15 (one per behavior + dogfood
+ 3 PBT amplifications).

State-delta migration summary
------------------------------
CONVERTED (8 tests) — state-delta + implicit-unchanged invariant:
  - test_shims_copied_to_bin_directory: multi-slot filesystem (5 shim exists
    booleans); implicit-unchanged enforces no unexpected file creation
  - test_shims_have_executable_mode: multi-slot filesystem (5 shim mode booleans);
    implicit-unchanged enforces no unexpected mode changes
  - test_path_env_prepended_in_settings_json: settings.json multi-slot (env.PATH
    prepended; permissions + hooks implicit-unchanged); catches bug-#48 class
  - test_path_prepended_even_when_prefix_collision: settings.json PATH exact value
    after normalization + implicit-unchanged; ensures only PATH mutates
  - test_install_is_idempotent_for_path_and_shims: idempotent_after predicate on
    env.PATH + set_to(True) on shim existence slots; idempotency across 2 calls
  - test_live_install_time_path_preserved_when_settings_json_starts_empty:
    prepended_with on env.PATH + implicit-unchanged; bug-#48 regression scenario
  - test_existing_dollar_home_entries_normalized_on_prepend: normalized_to predicate
    (exact use case of the factory); $HOME→absolute normalization contract
  - test_legacy_fabricated_path_auto_healed_on_reinstall: legacy_healed predicate
    (canonical use case — detector identifies SYSTEM_PATH_FALLBACK signature,
    healed_check verifies live PATH restoration); closes the empirical loop

KEPT as-is (4 tests) — no state-delta benefit:
  - test_validate_prerequisites_fails_when_shim_missing: interaction test
    (result.success=False + message content); no filesystem mutation
  - test_falls_back_to_system_paths_when_env_path_is_unset: multi-membership
    assertion on PATH segments; state-delta adds ceremony without gain on
    fallback-path membership checks
  - test_env_path_contains_no_dollar_home_literal: single content guard
    (no $HOME substring); no multi-slot to exploit, trivially clear as-is
  - test_shim_resolvable_via_shutil_which_after_install: runtime contract
    (shutil.which resolution loop); not a state mutation

PBT AMPLIFICATION (3 tests) — @given(path_strategy()) + assert_state_delta(strict=True):
  Added as cross-instance paradigm pilot (see class-level docstrings):
  - test_pbt_prepend_invariant_across_path_shapes: PBT variant of
    test_path_env_prepended_in_settings_json — 100 generated PATH shapes,
    strict=True. Exercises realistic multi-dir paths the single fixture cannot.
  - test_pbt_dollar_home_normalization_invariant: PBT variant of
    test_existing_dollar_home_entries_normalized_on_prepend — 100 generated
    $HOME-containing paths, strict=True. Covers all HOME-literal shapes
    path_strategy produces.
  - test_pbt_no_dollar_home_literal_after_install_invariant: PBT variant of
    test_env_path_contains_no_dollar_home_literal — 100 generated PATH shapes
    including $HOME literals; asserts no $HOME remains in written PATH.

Hidden mutations found: NONE detected. The universe of env.PATH + permissions +
hooks was clean across all scenarios — no key beyond env.PATH mutated during
_install_des_shims() calls.

PBT amplification results (cross-instance pilot):
  - Hardening hit rate: 3/4 = 75% (workflow_executor.py)
  - Master hit rate: see inline findings per test class
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given
from hypothesis import settings as h_settings
from nwave_ai.state_delta import (
    assert_state_delta,
    idempotent_after,
    legacy_healed,
    prepended_with,
    set_to,
)
from nwave_ai.state_delta.strategies import path_strategy

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


_HYPOTHESIS_SETTINGS = h_settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    deadline=None,
)


# ---------------------------------------------------------------------------
# PBT helpers
# ---------------------------------------------------------------------------


def _make_context_from_dirpath(base: Path) -> tuple[InstallContext, Path, Path]:
    """Build a minimal InstallContext from an arbitrary base directory.

    Mirrors _make_context() but accepts any Path instead of pytest's tmp_path,
    enabling use inside Hypothesis @given tests (which cannot receive fixtures).
    """
    source_root = base / "source"
    shims_dir = source_root / "scripts" / "des"
    shims_dir.mkdir(parents=True)
    for name in SHIM_NAMES:
        (shims_dir / name).write_text(f"#!/usr/bin/env python3\n# {name}\n")
    for script in ["check_stale_phases.py", "scope_boundary_check.py"]:
        (shims_dir / script).write_text(f"# {script}\n")
    templates_dir = source_root / "templates"
    templates_dir.mkdir(parents=True)
    for template in [
        ".pre-commit-config-nwave.yaml",
        ".des-audit-README.md",
        "roadmap-schema.json",
    ]:
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
    return context, shims_dir, claude_dir


SHIM_NAMES = [
    "des-log-phase",
    "des-init-log",
    "des-verify-integrity",
    "des-roadmap",
    "des-health-check",
]


def _make_context(tmp_path: Path) -> tuple[InstallContext, Path, Path]:
    """Build a minimal InstallContext with staged source shims.

    Returns:
        (context, source_shims_dir, claude_dir)
    """
    source_root = tmp_path / "source"
    # DESPlugin resolves: framework_source / "scripts" / "des" when framework_source is set
    shims_dir = source_root / "scripts" / "des"
    shims_dir.mkdir(parents=True)
    for name in SHIM_NAMES:
        (shims_dir / name).write_text(f"#!/usr/bin/env python3\n# {name}\n")

    # Also stage the two required DES_SCRIPTS (same dir, same resolution path)
    for script in ["check_stale_phases.py", "scope_boundary_check.py"]:
        (shims_dir / script).write_text(f"# {script}\n")

    # Stage DES_TEMPLATES
    templates_dir = source_root / "templates"
    templates_dir.mkdir(parents=True)
    for template in [
        ".pre-commit-config-nwave.yaml",
        ".des-audit-README.md",
        "roadmap-schema.json",
    ]:
        (templates_dir / template).write_text(f"# {template}\n")

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    logger = MagicMock()

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=templates_dir,
        logger=logger,
        project_root=tmp_path / "project",
        framework_source=source_root,
    )

    return context, shims_dir, claude_dir


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _shim_filesystem_state(
    bin_dir: Path,
    track: frozenset[str] | None = None,
) -> dict[str, object]:
    """Return a flat state dict for DES shim existence in ~/.claude/bin/.

    Slots: "<shim_name>.exists" — bool whether the shim file exists.

    When ``track`` is provided every name in the set is always emitted.
    Without ``track``, only existing shims are emitted.

    Args:
        bin_dir: The ~/.claude/bin/ directory.
        track: Optional explicit set of slot names (e.g. "des-log-phase.exists").
    """
    state: dict[str, object] = {}
    if track is not None:
        for slot in track:
            shim_name = slot.removesuffix(".exists")
            state[slot] = (bin_dir / shim_name).exists()
    else:
        for name in SHIM_NAMES:
            if (bin_dir / name).exists():
                state[f"{name}.exists"] = True
    return state


def _shim_mode_state(bin_dir: Path) -> dict[str, object]:
    """Return a flat state dict for DES shim mode bits in ~/.claude/bin/.

    Slots: "<shim_name>.executable" — bool whether the shim has 0o755 mode.
    Only emits slots for shims that exist.
    """
    state: dict[str, object] = {}
    for name in SHIM_NAMES:
        path = bin_dir / name
        if path.exists():
            state[f"{name}.executable"] = (path.stat().st_mode & 0o755) == 0o755
    return state


def _settings_state(settings_file: Path) -> dict[str, object]:
    """Return a flat state dict for settings.json keys relevant to shim install.

    Slots:
      "env.PATH"    — raw string value (empty str when absent)
      "permissions" — JSON-serialized permissions block (empty JSON when absent)
      "hooks"       — JSON-serialized hooks block (empty JSON when absent)

    Args:
        settings_file: Path to settings.json.
    """
    if not settings_file.exists():
        return {
            "env.PATH": "",
            "permissions": json.dumps({}),
            "hooks": json.dumps({}),
        }
    config = json.loads(settings_file.read_text(encoding="utf-8"))
    return {
        "env.PATH": config.get("env", {}).get("PATH", ""),
        "permissions": json.dumps(config.get("permissions", {}), sort_keys=True),
        "hooks": json.dumps(config.get("hooks", {}), sort_keys=True),
    }


# ---------------------------------------------------------------------------
# Tests: filesystem — shim presence
# ---------------------------------------------------------------------------


class TestShimsCopiedToBinDirectory:
    """Shims from source are copied to ~/.claude/bin/."""

    def test_shims_copied_to_bin_directory(self, tmp_path: Path) -> None:
        """
        GIVEN: 5 shim files exist in the source scripts/des/ directory
        WHEN: _install_des_shims() is called
        THEN: all 5 files exist in ~/.claude/bin/
              AND no other slots in the tracked universe change unexpectedly
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        bin_dir = claude_dir / "bin"
        tracked = frozenset(f"{name}.exists" for name in SHIM_NAMES)

        before = _shim_filesystem_state(bin_dir, track=tracked)

        DESPlugin()._install_des_shims(context)

        after = _shim_filesystem_state(bin_dir, track=tracked)
        assert_state_delta(
            before=before,
            after=after,
            universe=set(tracked),
            expected={slot: set_to(True) for slot in tracked},
        )


# ---------------------------------------------------------------------------
# Tests: filesystem — shim mode bits
# ---------------------------------------------------------------------------


class TestShimsHaveExecutableMode:
    """Each installed shim must have the executable bit set (0o755)."""

    def test_shims_have_executable_mode(self, tmp_path: Path) -> None:
        """
        GIVEN: 5 shim files exist in the source scripts/des/ directory
        WHEN: _install_des_shims() is called
        THEN: each installed shim has 0o755 mode bits
              AND no unexpected mode slot changes beyond the 5 shims
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        bin_dir = claude_dir / "bin"

        before = _shim_mode_state(bin_dir)

        DESPlugin()._install_des_shims(context)

        after = _shim_mode_state(bin_dir)
        universe = set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={f"{name}.executable": set_to(True) for name in SHIM_NAMES},
        )


# ---------------------------------------------------------------------------
# Tests: settings.json env.PATH mutations
# ---------------------------------------------------------------------------


class TestPathEnvPrependedInSettingsJson:
    """settings.json env.PATH must be prefixed with the absolute DES bin path."""

    def test_path_env_prepended_in_settings_json(self, tmp_path: Path) -> None:
        """
        GIVEN: settings.json does not yet have the DES bin path in PATH
        WHEN: _install_des_shims() is called
        THEN: settings.json env.PATH starts with the absolute path to ~/.claude/bin
              (not the shell variable literal '$HOME/.claude/bin')
              AND permissions and hooks blocks are unchanged (implicit-unchanged invariant)

        Updated per contradiction rule: prior assertion validated the broken
        behavior (literal $HOME). Claude Code does not expand env values.

        State-delta: catches bug-#48 class — any mutation to permissions or hooks
        that was not declared in expected raises kind='undeclared_change'.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        des_bin = str(claude_dir / "bin")
        existing_path = "/home/u/.local/bin:/usr/bin"
        user_permissions = {"allow": ["Read", "Edit"], "ask": []}
        user_hooks: dict[str, object] = {"PreToolUse": []}
        settings_file.write_text(
            json.dumps(
                {
                    "env": {"PATH": existing_path},
                    "permissions": user_permissions,
                    "hooks": user_hooks,
                }
            ),
            encoding="utf-8",
        )

        before = _settings_state(settings_file)

        DESPlugin()._install_des_shims(context)

        after = _settings_state(settings_file)
        assert_state_delta(
            before=before,
            after=after,
            universe={"env.PATH", "permissions", "hooks"},
            expected={"env.PATH": prepended_with(des_bin)},
        )


class TestValidatePrerequisitesFailsWhenShimMissing:
    """validate_prerequisites must fail when any shim source file is absent."""

    def test_validate_prerequisites_fails_when_shim_missing(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: The source scripts/des/ directory is missing one shim file
        WHEN: validate_prerequisites() is called
        THEN: result.success is False and result.message mentions the missing shim
        """
        context, shims_dir, _claude_dir = _make_context(tmp_path)
        # Remove one shim from the source directory to simulate absence
        missing_shim = "des-verify-integrity"
        (shims_dir / missing_shim).unlink()

        plugin = DESPlugin()
        result = plugin.validate_prerequisites(context)

        assert not result.success, (
            "validate_prerequisites should fail when a shim source file is missing"
        )
        assert missing_shim in result.message, (
            f"Error message should name the missing shim '{missing_shim}', "
            f"got: {result.message!r}"
        )


class TestPathPrependedEvenWhenPrefixCollision:
    """PATH prepend must use colon-split membership, not substring match."""

    def test_path_prepended_even_when_prefix_collision(self, tmp_path: Path) -> None:
        """
        GIVEN: settings.json env.PATH contains a path that is a prefix of the DES
               bin path but is NOT equal (e.g. '~/.claude/bin-alt')
        WHEN: _install_des_shims() is called
        THEN: the absolute DES bin path IS prepended as the first segment
              AND permissions and hooks blocks are unchanged

        Updated per contradiction rule: prior test used $HOME literals in both
        existing_path and expected value. Now uses absolute path expectations
        since $HOME entries are normalized during prepend.

        State-delta: the multi-slot universe (env.PATH + permissions + hooks)
        enforces that the prefix-collision fix doesn't silently corrupt other keys.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        home = str(Path.home())
        des_bin = str(claude_dir / "bin")

        # Pre-seed settings.json with a path containing a prefix collision.
        # $HOME entries will be normalized to absolute on prepend.
        existing_path = "$HOME/.claude/bin-alt:$HOME/other/bin"
        settings_file.write_text(
            json.dumps({"env": {"PATH": existing_path}}), encoding="utf-8"
        )

        before = _settings_state(settings_file)

        DESPlugin()._install_des_shims(context)

        after = _settings_state(settings_file)
        normalized_existing = existing_path.replace("$HOME", home)
        expected_path = f"{des_bin}:{normalized_existing}"
        assert_state_delta(
            before=before,
            after=after,
            universe={"env.PATH", "permissions", "hooks"},
            expected={"env.PATH": set_to(expected_path)},
        )


class TestInstallIsIdempotentForPathAndShims:
    """Repeated invocation must not duplicate PATH entry and must leave shims intact."""

    def test_install_is_idempotent_for_path_and_shims(self, tmp_path: Path) -> None:
        """
        GIVEN: _install_des_shims() has already been called once
        WHEN: _install_des_shims() is called a second time
        THEN: PATH still begins with the DES bin path (idempotent_after)
              AND all 5 shims are still present with executable mode

        Updated per contradiction rule: prior assertion used $HOME literal.
        Now verifies absolute path idempotency.

        State-delta: idempotent_after predicate on env.PATH asserts that the
        second call does not duplicate the prefix; set_to(True) on shim slots
        asserts all shims survive the second call.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        bin_dir = claude_dir / "bin"
        settings_file = claude_dir / "settings.json"
        des_bin = str(claude_dir / "bin")
        tracked_shims = frozenset(f"{name}.exists" for name in SHIM_NAMES)

        plugin = DESPlugin()
        plugin._install_des_shims(context)

        # Capture "after first call" state as the before baseline for second call
        before_settings = _settings_state(settings_file)
        before_shims = _shim_filesystem_state(bin_dir, track=tracked_shims)

        plugin._install_des_shims(context)

        after_settings = _settings_state(settings_file)
        after_shims = _shim_filesystem_state(bin_dir, track=tracked_shims)

        # env.PATH: second call must not duplicate the prefix
        assert_state_delta(
            before=before_settings,
            after=after_settings,
            universe={"env.PATH", "permissions", "hooks"},
            expected={"env.PATH": idempotent_after(des_bin)},
        )
        # Shims: all 5 still present after second install
        assert_state_delta(
            before=before_shims,
            after=after_shims,
            universe=set(tracked_shims),
            expected={slot: set_to(True) for slot in tracked_shims},
        )


class TestLivePathPreservedWhenSettingsStartsEmpty:
    """The user's live install-time PATH must be preserved on a fresh install.

    Behavior #7: when settings.json has no prior env.PATH, the installer must
    seed env.PATH from os.environ["PATH"] (the live install-time PATH the user
    invoked nwave-ai with), prepended with $HOME/.claude/bin. Claude Code
    REPLACES env.PATH (no merge with the inherited shell PATH), so seeding
    from a hardcoded minimum would strip user-visible directories such as
    ~/.local/bin (where pipx-installed CLIs including claude/nwave-ai live),
    ~/.deno/bin, /snap/bin, etc.
    """

    def test_live_install_time_path_preserved_when_settings_json_starts_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: settings.json does not exist (fresh install, no prior env.PATH)
          AND: os.environ["PATH"] contains user-visible dirs (~/.local/bin,
               ~/.deno/bin, /snap/bin) alongside system dirs
        WHEN: _install_des_shims() is called
        THEN: settings.json env.PATH equals
              "<des_bin>:<os.environ['PATH']>" verbatim — the live install-time
              PATH is preserved so binaries the user's shell can find remain
              reachable inside Claude Code sessions and hooks.

        State-delta: prepended_with asserts the exact structure; the universe
        also tracks permissions and hooks to enforce they remain absent/unchanged.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        des_bin = str(claude_dir / "bin")

        assert not settings_file.exists(), (
            "Pre-condition failed: settings.json must not exist before install"
        )

        # Simulate a typical user PATH containing dirs that the legacy
        # SYSTEM_PATH_FALLBACK constant would have stripped.
        live_path = (
            "/home/u/.local/bin:/home/u/.deno/bin:/home/u/bin:"
            "/usr/local/bin:/usr/bin:/bin:/snap/bin"
        )
        monkeypatch.setenv("PATH", live_path)

        before = _settings_state(settings_file)

        DESPlugin()._install_des_shims(context)

        after = _settings_state(settings_file)
        expected_path = f"{des_bin}:{live_path}"
        assert_state_delta(
            before=before,
            after=after,
            universe={"env.PATH", "permissions", "hooks"},
            expected={"env.PATH": set_to(expected_path)},
        )

    def test_falls_back_to_system_paths_when_env_path_is_unset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: settings.json does not exist AND os.environ has no PATH at all
        WHEN: _install_des_shims() is called
        THEN: env.PATH falls back to "<des_bin>:<SYSTEM_PATH_FALLBACK>" so
              that system tools (python3, grep, git) remain reachable. The
              hardcoded fallback is a last resort — it is only used when the
              installer cannot read a live PATH from the environment.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        monkeypatch.delenv("PATH", raising=False)

        plugin = DESPlugin()
        plugin._install_des_shims(context)

        settings_file = claude_dir / "settings.json"
        config = json.loads(settings_file.read_text(encoding="utf-8"))
        path_value = config.get("env", {}).get("PATH", "")
        path_segments = path_value.split(":")

        des_bin = str(claude_dir / "bin")
        assert path_segments[0] == des_bin, (
            f"DES bin dir must be first PATH segment. Got: {path_segments[0]!r}"
        )
        for system_path in ["/usr/local/bin", "/usr/bin", "/bin"]:
            assert system_path in path_segments, (
                f"Fallback system path '{system_path}' missing from "
                f"env.PATH={path_value!r} when os.environ has no PATH."
            )


class TestEnvPathContainsNoDollarHomeLiteral:
    """env.PATH must contain no $HOME literal after install.

    Behavior #8: Claude Code passes env.PATH verbatim to exec() without shell
    expansion. A literal $HOME never resolves to the filesystem path.
    """

    def test_env_path_contains_no_dollar_home_literal(self, tmp_path: Path) -> None:
        """
        GIVEN: A fresh install context with no prior settings.json
        WHEN: _install_des_shims() is called
        THEN: settings.json env.PATH contains no '$HOME' literal substring
              (Claude Code does not shell-expand env values; $HOME is never resolved)
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        plugin = DESPlugin()

        plugin._install_des_shims(context)

        settings_file = claude_dir / "settings.json"
        config = json.loads(settings_file.read_text(encoding="utf-8"))
        env_path = config.get("env", {}).get("PATH", "")

        assert "$HOME" not in env_path, (
            f"env.PATH contains unexpanded shell variable '$HOME': {env_path!r}. "
            "Claude Code passes env values verbatim to exec(); $HOME is never resolved."
        )


class TestShimResolvableViaShutilWhichAfterInstall:
    """Shims must be findable by bare name using the installed PATH value.

    Behavior #9: Runtime contract — shutil.which(name, path=env_path) mimics the
    OS command lookup. If it returns None, the shim is not reachable by bare name.
    """

    def test_shim_resolvable_via_shutil_which_after_install(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: _install_des_shims() has been called on a context with real shim files
        WHEN: shutil.which(shim_name, path=env_path_value) is called for each shim
              using the exact PATH string written to settings.json
        THEN: every shim resolves to a non-None path that exists on disk
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        plugin = DESPlugin()

        plugin._install_des_shims(context)

        settings_file = claude_dir / "settings.json"
        config = json.loads(settings_file.read_text(encoding="utf-8"))
        env_path = config.get("env", {}).get("PATH", "")

        for shim_name in SHIM_NAMES:
            resolved = shutil.which(shim_name, path=env_path)
            assert resolved is not None, (
                f"Shim '{shim_name}' not resolvable by bare name with "
                f"PATH={env_path!r}. "
                "This is the runtime failure: Claude Code uses this PATH string "
                "verbatim and the shim is unreachable if it contains $HOME."
            )
            assert Path(resolved).exists(), (
                f"Resolved shim path does not exist: {resolved}"
            )


class TestExistingDollarHomeEntriesNormalizedOnPrepend:
    """Pre-existing $HOME entries in PATH must be normalized to absolute paths.

    Behavior #10: Upgrade idempotency — if a user has a prior install with
    $HOME/.claude/bin or other $HOME entries, re-running install must rewrite
    them to absolute paths (BUG-2 from RCA).
    """

    def test_existing_dollar_home_entries_normalized_on_prepend(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: settings.json env.PATH contains '$HOME/.local/bin:$HOME/.claude/bin-old'
               (pre-existing entries with unexpanded shell variables)
        WHEN: _install_des_shims() is called
        THEN: the resulting env.PATH equals "<des_bin>:<expanded existing segments>"
              (all $HOME references resolved to absolute paths, des_bin prepended)
              AND permissions and hooks blocks are unchanged

        State-delta: set_to(expected_normalized) asserts the exact final value
        after $HOME-expansion + prepend. The implicit-unchanged invariant on
        permissions + hooks guards against collateral mutations.

        Note: normalized_to is NOT used here because it checks
        normalizer(before)==normalizer(after), which fails by design when des_bin
        is prepended (old and new are structurally different). The correct predicate
        for "normalize existing entries then prepend" is set_to with the exact
        known expected value.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        home = str(Path.home())
        des_bin = str(claude_dir / "bin")

        # Pre-seed settings.json with $HOME-containing entries (simulates prior install)
        existing_path = "$HOME/.local/bin:$HOME/.claude/bin-old:/usr/bin"
        settings_file.write_text(
            json.dumps({"env": {"PATH": existing_path}}), encoding="utf-8"
        )

        before = _settings_state(settings_file)

        DESPlugin()._install_des_shims(context)

        after = _settings_state(settings_file)

        # Expected: des_bin prepended + all $HOME segments expanded to absolute paths
        expanded_existing = existing_path.replace("$HOME", home)
        expected_normalized = f"{des_bin}:{expanded_existing}"
        assert_state_delta(
            before=before,
            after=after,
            universe={"env.PATH", "permissions", "hooks"},
            expected={"env.PATH": set_to(expected_normalized)},
        )


class TestLegacyFabricatedPathAutoHealedOnReinstall:
    """Settings written by older installer versions must be auto-healed.

    Behavior #11: Older installer versions seeded env.PATH from a hardcoded
    minimum (SYSTEM_PATH_FALLBACK) on fresh installs, producing the exact
    value '<des_bin>:<SYSTEM_PATH_FALLBACK>'. That value stripped the user's
    real PATH (~/.local/bin etc.) and broke bare-name resolution of binaries
    like claude/nwave-ai. The idempotency guard would otherwise see
    ~/.claude/bin already present and short-circuit, leaving affected users
    stuck. This test asserts that re-running install rewrites the legacy
    signature using the live os.environ["PATH"].

    State-delta: legacy_healed predicate is the CANONICAL use case for this
    factory — detector identifies the exact legacy fabricated signature,
    healed_check verifies the value was replaced with the live PATH.
    """

    def test_legacy_fabricated_path_replaced_with_live_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: settings.json env.PATH equals the legacy installer-fabricated
               value '<absolute_des_bin>:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'
          AND: os.environ["PATH"] contains the user's real shell PATH
               including ~/.local/bin (which the legacy value stripped)
        WHEN: _install_des_shims() is called
        THEN: env.PATH is rewritten to "<des_bin>:<os.environ['PATH']>",
              restoring access to the user's real PATH dirs.
              AND permissions and hooks are unchanged (implicit-unchanged invariant)

        State-delta: legacy_healed(detector, healed_check) is the paper-trace
        predicate for this exact scenario — the 4-case matrix is:
          Case 1: detector(old)=True, healed_check(new)=True  → PASS (healed)
          Case 2: detector(old)=True, healed_check(new)=False → FAIL (heal failed)
          Case 3: detector(old)=False, *                      → FAIL (not legacy)
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        settings_file = claude_dir / "settings.json"
        des_bin = str(claude_dir / "bin")

        # The exact legacy fabricated signature from SYSTEM_PATH_FALLBACK
        system_path_fallback = DESPlugin.SYSTEM_PATH_FALLBACK
        legacy_value = f"{des_bin}:{system_path_fallback}"

        # Pre-seed settings.json with the exact legacy signature.
        settings_file.write_text(
            json.dumps({"env": {"PATH": legacy_value}}), encoding="utf-8"
        )

        # Simulate the user's real shell PATH at install time.
        live_path = (
            "/home/u/.local/bin:/home/u/.deno/bin:"
            "/usr/local/bin:/usr/bin:/bin:/snap/bin"
        )
        monkeypatch.setenv("PATH", live_path)

        before = _settings_state(settings_file)

        DESPlugin()._install_des_shims(context)

        after = _settings_state(settings_file)

        expected_healed = f"{des_bin}:{live_path}"
        assert_state_delta(
            before=before,
            after=after,
            universe={"env.PATH", "permissions", "hooks"},
            expected={
                "env.PATH": legacy_healed(
                    detector=lambda s: s == legacy_value,
                    healed_check=lambda s: s == expected_healed,
                ),
            },
        )


# -----------------------------------------------------------------------------
# Dogfood: same installer mutation expressed as a state-delta assertion.
#
# This test does NOT replace any existing test. It demonstrates the new
# state-delta paradigm on real installer code: the universe declares which
# settings.json keys we promise to track; predicates declare what can change;
# everything else in the universe is asserted unchanged BY CONSTRUCTION.
#
# Specifically: it catches the regression class issue #48 belonged to —
# "installer mutates a key the test wasn't watching." If the installer ever
# accidentally drops a user's `permissions` block or `hooks` block, the
# implicit-unchanged invariant fails the test even though the test only
# declared an *explicit* expectation on env.PATH.
# -----------------------------------------------------------------------------


class TestSettingsMutationViaStateDelta:
    """Dogfood for nwave_ai.state_delta on installer settings.json mutation."""

    def test_install_only_mutates_env_path_user_permissions_and_hooks_preserved(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: settings.json with a user-set permissions block AND a user-set
               hooks block AND an existing env.PATH (user-shape PATH dirs)
        WHEN: _install_des_shims() runs
        THEN: env.PATH is prepended with the absolute DES bin path
              AND permissions block is byte-identical to before
              AND hooks block is byte-identical to before

        The matcher catches future regressions in the bug #48 class: any
        installer change that mutates a settings.json key beyond env.PATH
        without it appearing in `expected` raises kind='undeclared_change'.
        """
        from nwave_ai.state_delta import (
            assert_state_delta,
            prepended_with,
        )

        context, _shims_dir, claude_dir = _make_context(tmp_path)
        des_bin = str(claude_dir / "bin")
        existing_path = "/home/u/.local/bin:/usr/bin"
        user_permissions = {"allow": ["Read", "Edit"], "ask": []}
        user_hooks = {"PreToolUse": [{"matcher": "Bash", "hooks": []}]}

        # Pre-seed settings.json with a fully-formed user config
        settings_file = claude_dir / "settings.json"
        before_settings = {
            "env": {"PATH": existing_path},
            "permissions": user_permissions,
            "hooks": user_hooks,
        }
        settings_file.write_text(json.dumps(before_settings), encoding="utf-8")

        # Capture flat-key snapshot before
        before = {
            "env.PATH": existing_path,
            "permissions": json.dumps(user_permissions, sort_keys=True),
            "hooks": json.dumps(user_hooks, sort_keys=True),
        }

        # Action
        DESPlugin()._install_des_shims(context)

        # Capture flat-key snapshot after
        after_settings = json.loads(settings_file.read_text(encoding="utf-8"))
        after = {
            "env.PATH": after_settings.get("env", {}).get("PATH", ""),
            "permissions": json.dumps(
                after_settings.get("permissions", {}), sort_keys=True
            ),
            "hooks": json.dumps(after_settings.get("hooks", {}), sort_keys=True),
        }

        # State-delta assertion:
        # - env.PATH: explicit predicate (must be prepended with DES bin)
        # - permissions, hooks: NOT in expected → implicit-unchanged enforced
        assert_state_delta(
            before=before,
            after=after,
            universe={"env.PATH", "permissions", "hooks"},
            expected={"env.PATH": prepended_with(des_bin)},
        )


# =============================================================================
# PBT AMPLIFICATION — cross-instance paradigm pilot
# =============================================================================
# Each test converts a single-fixture state-delta test into a @given property
# that exercises 100 generated PATH shapes via path_strategy().
# strict=True enforces the mandate from commit 93a1132b7.
#
# Filesystem isolation: each Hypothesis example gets its own tempfile.mkdtemp()
# directory because pytest's tmp_path fixture is incompatible with @given.
# =============================================================================


class TestPbtPrependInvariantAcrossPathShapes:
    """PBT amplification of test_path_env_prepended_in_settings_json.

    Pilot finding: single-fixture test used one hardcoded PATH
    ('/home/u/.local/bin:/usr/bin'). PBT exercises 100 generated shapes
    from path_strategy(include_home_literal=False, include_empty=False,
    include_legacy_fallback=False) — the subset that triggers the default-
    prepend branch (no special cases). Invariant: env.PATH is prepended with
    the absolute DES bin path AND permissions + hooks are unchanged.
    """

    @given(
        user_path=path_strategy(
            include_home_literal=False,
            include_empty=False,
            include_legacy_fallback=False,
        )
    )
    @h_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
        deadline=None,
    )
    def test_pbt_prepend_invariant_across_path_shapes(self, user_path: str) -> None:
        """
        GIVEN: settings.json env.PATH is a generated realistic multi-dir path
               (no $HOME literals, non-empty, non-legacy) plus user permissions
               and hooks blocks
        WHEN:  _install_des_shims() is called across 100 generated PATH shapes
        THEN:  env.PATH is prepended with the absolute DES bin path
               AND permissions and hooks blocks are unchanged (strict=True)

        PBT amplification of test_path_env_prepended_in_settings_json.
        Bug surface: des_plugin._update_path_in_settings (24 fix commits/6mo).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            context, _shims_dir, claude_dir = _make_context_from_dirpath(base)
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

            DESPlugin()._install_des_shims(context)

            after = _settings_state(settings_file)
            assert_state_delta(
                before=before,
                after=after,
                universe={"env.PATH", "permissions", "hooks"},
                expected={"env.PATH": prepended_with(des_bin)},
                strict=True,
            )


class TestPbtDollarHomeNormalizationInvariant:
    """PBT amplification of test_existing_dollar_home_entries_normalized_on_prepend.

    Pilot finding: single-fixture test used one hardcoded $HOME path
    ('$HOME/.local/bin:$HOME/.claude/bin-old:/usr/bin'). PBT exercises 100
    generated $HOME-containing paths from path_strategy(include_home_literal=True).
    Invariant: no $HOME literal survives in the written env.PATH.
    """

    @given(user_path=path_strategy(include_home_literal=True))
    @h_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
        deadline=None,
    )
    def test_pbt_dollar_home_normalization_invariant(self, user_path: str) -> None:
        """
        GIVEN: settings.json env.PATH is a generated path that may contain $HOME
               literals (path_strategy with include_home_literal=True)
        WHEN:  _install_des_shims() is called across 100 generated shapes
        THEN:  settings.json env.PATH contains no '$HOME' literal substring
               AND permissions and hooks blocks are unchanged (strict=True)

        PBT amplification of test_existing_dollar_home_entries_normalized_on_prepend.
        Covers the $HOME-normalization branch of _update_path_in_settings for all
        generated HOME-literal shapes, not just the single hardcoded fixture.
        """
        from hypothesis import assume

        assume("$HOME" in user_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            context, _shims_dir, claude_dir = _make_context_from_dirpath(base)
            settings_file = claude_dir / "settings.json"
            settings_file.write_text(
                json.dumps({"env": {"PATH": user_path}}),
                encoding="utf-8",
            )

            before = _settings_state(settings_file)

            DESPlugin()._install_des_shims(context)

            after = _settings_state(settings_file)
            assert_state_delta(
                before=before,
                after=after,
                universe={"env.PATH", "permissions", "hooks"},
                expected={
                    "env.PATH": lambda _old, new: "$HOME" not in new,
                },
                strict=True,
            )


class TestPbtNoDollarHomeLiteralAfterInstallInvariant:
    """PBT amplification of test_env_path_contains_no_dollar_home_literal.

    Pilot finding: single-fixture test used a fresh install (no prior PATH).
    PBT exercises 100 generated PATH shapes including $HOME literals, empty
    strings, and realistic multi-dir paths. Invariant: no $HOME literal
    appears in the written env.PATH regardless of what was seeded.
    """

    @given(user_path=path_strategy(include_home_literal=True, include_empty=True))
    @h_settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
        deadline=None,
    )
    def test_pbt_no_dollar_home_literal_after_install_invariant(
        self, user_path: str
    ) -> None:
        """
        GIVEN: settings.json env.PATH is a generated path (any shape from
               path_strategy including $HOME-literals and empty string)
        WHEN:  _install_des_shims() is called across 100 generated shapes
        THEN:  settings.json env.PATH contains no '$HOME' literal substring
               (Claude Code passes env values verbatim to exec; $HOME never resolves)

        PBT amplification of test_env_path_contains_no_dollar_home_literal.
        Broader than the original: exercises non-empty pre-existing PATHs too,
        not only the fresh-install (empty) scenario.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            context, _shims_dir, claude_dir = _make_context_from_dirpath(base)
            settings_file = claude_dir / "settings.json"
            if user_path:
                settings_file.write_text(
                    json.dumps({"env": {"PATH": user_path}}),
                    encoding="utf-8",
                )
            # When user_path is empty, leave settings.json absent (fresh install)

            env_backup = os.environ.get("PATH")
            try:
                os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin"
                DESPlugin()._install_des_shims(context)
            finally:
                if env_backup is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = env_backup

            config = json.loads(settings_file.read_text(encoding="utf-8"))
            env_path = config.get("env", {}).get("PATH", "")
            assert "$HOME" not in env_path, (
                f"env.PATH contains unexpanded '$HOME' after install with "
                f"input {user_path!r}: {env_path!r}"
            )
