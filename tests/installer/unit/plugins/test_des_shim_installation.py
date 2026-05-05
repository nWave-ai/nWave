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

Test budget: 11 behaviors x 2 = 22 max tests. Using 11 (one per behavior).
"""

import json
import shutil
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


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


class TestShimsCopiedToBinDirectory:
    """Shims from source are copied to ~/.claude/bin/."""

    def test_shims_copied_to_bin_directory(self, tmp_path: Path) -> None:
        """
        GIVEN: 5 shim files exist in the source scripts/des/ directory
        WHEN: _install_des_shims() is called
        THEN: all 5 files exist in ~/.claude/bin/
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        plugin = DESPlugin()

        plugin._install_des_shims(context)

        bin_dir = claude_dir / "bin"
        for name in SHIM_NAMES:
            assert (bin_dir / name).exists(), f"Shim not found: {name}"


class TestShimsHaveExecutableMode:
    """Each installed shim must have the executable bit set (0o755)."""

    def test_shims_have_executable_mode(self, tmp_path: Path) -> None:
        """
        GIVEN: 5 shim files exist in the source scripts/des/ directory
        WHEN: _install_des_shims() is called
        THEN: each installed shim has mode bits 0o755 (owner rwx, group rx, other rx)
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        plugin = DESPlugin()

        plugin._install_des_shims(context)

        bin_dir = claude_dir / "bin"
        for name in SHIM_NAMES:
            path = bin_dir / name
            file_mode = path.stat().st_mode
            assert file_mode & 0o755 == 0o755, (
                f"{name}: expected mode 0o755, got {oct(stat.S_IMODE(file_mode))}"
            )


class TestPathEnvPrependedInSettingsJson:
    """settings.json env.PATH must be prefixed with the absolute DES bin path."""

    def test_path_env_prepended_in_settings_json(self, tmp_path: Path) -> None:
        """
        GIVEN: settings.json does not yet have the DES bin path in PATH
        WHEN: _install_des_shims() is called
        THEN: settings.json env.PATH starts with the absolute path to ~/.claude/bin
              (not the shell variable literal '$HOME/.claude/bin')

        Updated per contradiction rule: prior assertion validated the broken
        behavior (literal $HOME). Claude Code does not expand env values.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        plugin = DESPlugin()

        plugin._install_des_shims(context)

        settings_file = claude_dir / "settings.json"
        assert settings_file.exists(), "settings.json was not created"
        config = json.loads(settings_file.read_text(encoding="utf-8"))
        path_value = config.get("env", {}).get("PATH", "")
        expected_prefix = str(claude_dir / "bin")
        assert path_value.startswith(expected_prefix), (
            f"PATH does not start with absolute DES bin path {expected_prefix!r}: "
            f"{path_value!r}"
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

        Updated per contradiction rule: prior test used $HOME literals in both
        existing_path and expected value. Now uses absolute path expectations
        since $HOME entries are normalized during prepend.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)

        # Pre-seed settings.json with a path containing a prefix collision.
        # $HOME entries will be normalized to absolute on prepend.
        home = str(Path.home())
        existing_path = "$HOME/.claude/bin-alt:$HOME/other/bin"
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(
            json.dumps({"env": {"PATH": existing_path}}), encoding="utf-8"
        )

        plugin = DESPlugin()
        plugin._install_des_shims(context)

        config = json.loads(settings_file.read_text(encoding="utf-8"))
        path_value = config.get("env", {}).get("PATH", "")

        # DES bin path prepended; existing $HOME entries normalized to absolute
        des_bin = str(claude_dir / "bin")
        normalized_existing = existing_path.replace("$HOME", home)
        expected = f"{des_bin}:{normalized_existing}"
        assert path_value == expected, (
            f"Expected PATH={expected!r}, got {path_value!r}. "
            "Substring match incorrectly skipped prepend due to prefix collision."
        )


class TestInstallIsIdempotentForPathAndShims:
    """Repeated invocation must not duplicate PATH entry and must leave shims intact."""

    def test_install_is_idempotent_for_path_and_shims(self, tmp_path: Path) -> None:
        """
        GIVEN: _install_des_shims() has already been called once
        WHEN: _install_des_shims() is called a second time
        THEN: PATH contains exactly one occurrence of the absolute DES bin path
              and all 5 shims are still present with executable mode

        Updated per contradiction rule: prior assertion used $HOME literal.
        Now verifies absolute path idempotency.
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        plugin = DESPlugin()

        plugin._install_des_shims(context)
        plugin._install_des_shims(context)

        settings_file = claude_dir / "settings.json"
        config = json.loads(settings_file.read_text(encoding="utf-8"))
        path_value = config.get("env", {}).get("PATH", "")
        des_bin = str(claude_dir / "bin")

        # Exactly one occurrence of the absolute DES bin path
        assert path_value.count(des_bin) == 1, (
            f"PATH contains duplicate DES bin entry '{des_bin}': {path_value!r}"
        )

        # All shims still present and executable
        bin_dir = claude_dir / "bin"
        for name in SHIM_NAMES:
            path = bin_dir / name
            assert path.exists(), f"Shim missing after second install: {name}"
            assert path.stat().st_mode & 0o111 != 0, (
                f"{name}: executable bit lost after second install"
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
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        assert not (claude_dir / "settings.json").exists(), (
            "Pre-condition failed: settings.json must not exist before install"
        )

        # Simulate a typical user PATH containing dirs that the legacy
        # SYSTEM_PATH_FALLBACK constant would have stripped.
        live_path = (
            "/home/u/.local/bin:/home/u/.deno/bin:/home/u/bin:"
            "/usr/local/bin:/usr/bin:/bin:/snap/bin"
        )
        monkeypatch.setenv("PATH", live_path)

        plugin = DESPlugin()
        plugin._install_des_shims(context)

        settings_file = claude_dir / "settings.json"
        config = json.loads(settings_file.read_text(encoding="utf-8"))
        path_value = config.get("env", {}).get("PATH", "")

        des_bin = str(claude_dir / "bin")
        expected = f"{des_bin}:{live_path}"
        assert path_value == expected, (
            f"Expected env.PATH={expected!r}, got {path_value!r}. "
            "On a fresh install the user's live install-time PATH must be "
            "preserved verbatim and prefixed with the DES bin dir."
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
        THEN: the resulting env.PATH contains no '$HOME' literal
              AND the absolute DES bin path is present as the first segment
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)

        # Pre-seed settings.json with $HOME-containing entries (simulates prior install)
        existing_path = "$HOME/.local/bin:$HOME/.claude/bin-old:/usr/bin"
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(
            json.dumps({"env": {"PATH": existing_path}}), encoding="utf-8"
        )

        plugin = DESPlugin()
        plugin._install_des_shims(context)

        config = json.loads(settings_file.read_text(encoding="utf-8"))
        env_path = config.get("env", {}).get("PATH", "")

        assert "$HOME" not in env_path, (
            f"env.PATH still contains '$HOME' literal after install: {env_path!r}. "
            "Pre-existing $HOME entries must be normalized to absolute paths."
        )
        # The DES bin path must be first
        segments = env_path.split(":")
        expected_des_bin = str(context.claude_dir / "bin")
        assert segments[0] == expected_des_bin, (
            f"DES bin path must be first segment. "
            f"Expected: {expected_des_bin!r}, got: {segments[0]!r}"
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
        """
        context, _shims_dir, claude_dir = _make_context(tmp_path)
        des_bin = str(claude_dir / "bin")

        # Pre-seed settings.json with the exact legacy signature.
        legacy_value = f"{des_bin}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(
            json.dumps({"env": {"PATH": legacy_value}}), encoding="utf-8"
        )

        # Simulate the user's real shell PATH at install time.
        live_path = (
            "/home/u/.local/bin:/home/u/.deno/bin:"
            "/usr/local/bin:/usr/bin:/bin:/snap/bin"
        )
        monkeypatch.setenv("PATH", live_path)

        plugin = DESPlugin()
        plugin._install_des_shims(context)

        config = json.loads(settings_file.read_text(encoding="utf-8"))
        path_value = config.get("env", {}).get("PATH", "")

        expected = f"{des_bin}:{live_path}"
        assert path_value == expected, (
            f"Auto-heal failed. Expected env.PATH={expected!r}, got "
            f"{path_value!r}. Legacy installer-fabricated PATH value should be "
            "rewritten from os.environ['PATH'] on re-install."
        )
