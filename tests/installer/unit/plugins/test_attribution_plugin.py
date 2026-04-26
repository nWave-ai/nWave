"""Unit tests for AttributionPlugin.

Tests validate install-time consent flow through the driving port
(AttributionPlugin.install/verify) and assert at driven port boundaries
(global-config.json file system).

Test Budget: 6 behaviors x 2 = 12 max. Using 6 tests (1 per behavior).

Behaviors tested:
1. Interactive accept default -> attribution enabled in config
2. Interactive decline -> attribution disabled in config
3. Non-interactive (no TTY) -> defaults off, no prompt issued
4. Existing preference -> prompt skipped (upgrade path)
5. Missing config directory -> created automatically
6. Plugin error -> never blocks core installation (exception-safe)
"""

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.install.attribution_utils import install_attribution_hook
from scripts.install.plugins.attribution_plugin import AttributionPlugin
from scripts.install.plugins.base import InstallContext


# Serialize tests touching .git/hooks/ to avoid xdist races on shared state.
pytestmark = pytest.mark.xdist_group("git_hooks")


# ---------------------------------------------------------------------------
# Guard fixture: snapshot .git/hooks/ before module, verify unchanged after.
# This is the safety net -- if the isolation fixture below is ever removed or
# bypassed, this guard will catch corruption of real git hooks.
# ---------------------------------------------------------------------------
def _snapshot_hooks_dir(hooks_dir: Path) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for every file in hooks_dir."""
    if not hooks_dir.is_dir():
        return {}
    snapshot = {}
    for entry in sorted(hooks_dir.iterdir()):
        if entry.is_file():
            content_hash = hashlib.sha256(entry.read_bytes()).hexdigest()
            snapshot[entry.name] = content_hash
    return snapshot


def _diff_snapshots(before: dict[str, str], after: dict[str, str]) -> str:
    """Produce a human-readable diff between two snapshots."""
    lines = []
    all_keys = sorted(set(before) | set(after))
    for key in all_keys:
        if key not in before:
            lines.append(f"  CREATED: {key}")
        elif key not in after:
            lines.append(f"  DELETED: {key}")
        elif before[key] != after[key]:
            lines.append(f"  MODIFIED: {key}")
    return "\n".join(lines)


@pytest.fixture(autouse=True, scope="module")
def guard_git_hooks():
    """Assert .git/hooks/ is never modified by tests in this module.

    Snapshots file names and SHA-256 hashes before the module runs,
    then verifies the directory is byte-identical after all tests complete.
    Failure means a test escaped isolation and corrupted real git hooks.
    """
    hooks_dir = Path(".git/hooks")
    before = _snapshot_hooks_dir(hooks_dir)
    yield
    after = _snapshot_hooks_dir(hooks_dir)
    assert before == after, (
        "Tests corrupted .git/hooks/ directory!\n"
        "Differences detected:\n"
        f"{_diff_snapshots(before, after)}\n\n"
        "This means the _isolate_hook_installation fixture failed to "
        "prevent real hook file modifications. Fix the isolation fixture."
    )


# ---------------------------------------------------------------------------
# Isolation fixture: mock install_attribution_hook in the attribution_plugin
# module to prevent tests from writing to the real .git/hooks/ directory.
# The plugin tests validate consent flow, not hook installation (tested
# separately in TestAttributionHookInstallation with subprocess mocks).
#
# Module-scoped autouse: applies to EVERY test class in this module
# (TestAttributionPluginInstall, TestAttributionPluginVerify,
# TestAttributionPluginMetadata, TestAttributionUpgradePreservation,
# TestAttributionHookInstallation) without requiring opt-in at the class
# or function level. This prevents regressions where a new test class
# forgets to request the fixture and accidentally runs the real hook
# installation against the project's .git/hooks/ directory.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="module")
def mock_install_attribution_hook(tmp_path_factory: pytest.TempPathFactory):
    """Prevent plugin.install() from calling real install_attribution_hook.

    The real function resolves hooks dir from the process's git config,
    which points to the project's .git/hooks/ -- corrupting it with a
    tmp_path-based hook script path that becomes invalid after the test.

    Module-scoped so the patch covers every test class, including future
    additions, with no per-class opt-in required.
    """
    mock_hooks_dir = tmp_path_factory.mktemp("attribution_mock_hooks")
    with patch(
        "scripts.install.plugins.attribution_plugin.install_attribution_hook",
        return_value=mock_hooks_dir / "prepare-commit-msg",
    ) as mock_hook:
        yield mock_hook


def _make_context(tmp_path: Path) -> InstallContext:
    """Create a minimal InstallContext with tmp_path-based directories."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=tmp_path / "templates",
        logger=MagicMock(),
        project_root=tmp_path / "project",
        metadata={"nwave_config_dir": tmp_path / ".nwave"},
    )


def _read_global_config(config_dir: Path) -> dict:
    """Read global-config.json from the given nwave config directory."""
    config_file = config_dir / "global-config.json"
    with open(config_file, encoding="utf-8") as f:
        return json.load(f)


class TestAttributionPluginInstall:
    """Tests for AttributionPlugin.install() driving port."""

    def test_interactive_accept_default(self, tmp_path: Path) -> None:
        """TTY present, empty input (default) -> attribution enabled."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value=""),
        ):
            mock_stdin.isatty.return_value = True
            result = plugin.install(context)

        assert result.success is True
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True
        assert (
            config["attribution"]["trailer"] == "Co-Authored-By: nWave <nwave@nwave.ai>"
        )

    def test_install_never_prompts(self, tmp_path: Path) -> None:
        """Install MUST be non-blocking -- never calls input() (Fabio RCA).

        Replaces the legacy interactive_decline test: install no longer
        prompts. Users opt out post-install via `nwave-ai attribution off`.
        See tests/bugs/installer/test_attribution_install_nonblocking.py
        for the full regression suite.
        """
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input") as mock_input,
        ):
            mock_stdin.isatty.return_value = True
            result = plugin.install(context)

        assert result.success is True
        mock_input.assert_not_called()
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True

    def test_non_interactive_defaults_on(self, tmp_path: Path) -> None:
        """No TTY -> attribution defaults to on, no prompt issued."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input") as mock_input,
        ):
            mock_stdin.isatty.return_value = False
            result = plugin.install(context)

        assert result.success is True
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True
        mock_input.assert_not_called()

    def test_existing_preference_skips_prompt(self, tmp_path: Path) -> None:
        """Config already has attribution key -> no prompt, preserve preference."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "global-config.json"
        existing_config = {
            "attribution": {
                "enabled": True,
                "trailer": "Co-Authored-By: nWave <nwave@nwave.ai>",
            }
        }
        config_file.write_text(json.dumps(existing_config), encoding="utf-8")

        plugin = AttributionPlugin(config_dir=nwave_dir)

        with patch("builtins.input") as mock_input:
            result = plugin.install(context)

        assert result.success is True
        mock_input.assert_not_called()
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True

    def test_missing_config_dir_created(self, tmp_path: Path) -> None:
        """Config directory does not exist -> created, preference stored."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave-fresh"
        assert not nwave_dir.exists()

        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="y"),
        ):
            mock_stdin.isatty.return_value = True
            result = plugin.install(context)

        assert result.success is True
        assert nwave_dir.exists()
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True

    def test_never_blocks_core_install(self, tmp_path: Path) -> None:
        """Plugin error returns success with warning, never blocks install."""
        context = _make_context(tmp_path)
        # Use a path that will cause write failure (file instead of directory)
        nwave_dir = tmp_path / ".nwave-bad"
        nwave_dir.mkdir(parents=True)
        # Create a file where global-config.json should be a file in a dir
        # that cannot be created (simulate write error)
        config_file = nwave_dir / "global-config.json"
        # Make the config file a directory to cause json.dump to fail
        config_file.mkdir(parents=True)

        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="y"),
        ):
            mock_stdin.isatty.return_value = True
            result = plugin.install(context)

        # Must succeed even on error -- never block core install
        assert result.success is True
        assert result.plugin_name == "attribution"


class TestAttributionPluginVerify:
    """Tests for AttributionPlugin.verify() driving port."""

    def test_verify_passes_with_attribution_key(self, tmp_path: Path) -> None:
        """Verify passes when config has attribution key."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "global-config.json"
        config_file.write_text(
            json.dumps({"attribution": {"enabled": True}}),
            encoding="utf-8",
        )

        plugin = AttributionPlugin(config_dir=nwave_dir)
        result = plugin.verify(context)

        assert result.success is True

    def test_verify_passes_without_config_file(self, tmp_path: Path) -> None:
        """Verify passes even without config file (attribution is optional)."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave-missing"
        plugin = AttributionPlugin(config_dir=nwave_dir)
        result = plugin.verify(context)

        # Attribution is optional -- missing config is valid
        assert result.success is True


class TestAttributionPluginMetadata:
    """Tests for plugin registration metadata."""

    def test_plugin_priority_is_200(self) -> None:
        """Plugin priority must be 200 (runs after all core plugins)."""
        plugin = AttributionPlugin()
        assert plugin.priority == 200

    def test_plugin_name_is_attribution(self) -> None:
        """Plugin name must be 'attribution'."""
        plugin = AttributionPlugin()
        assert plugin.name == "attribution"


class TestAttributionUpgradePreservation:
    """Tests for US-04: upgrade preserves attribution preference."""

    def test_upgrade_preserves_enabled(self, tmp_path: Path) -> None:
        """Existing enabled preference -> no prompt, preference preserved."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "global-config.json"
        config_file.write_text(
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

        with patch("builtins.input") as mock_input:
            result = plugin.install(context)

        assert result.success is True
        mock_input.assert_not_called()
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True
        assert (
            "preserved" in result.message.lower() or "enabled" in result.message.lower()
        )

    def test_upgrade_preserves_disabled(self, tmp_path: Path) -> None:
        """Existing disabled preference -> no prompt, preference preserved."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "global-config.json"
        config_file.write_text(
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

        with patch("builtins.input") as mock_input:
            result = plugin.install(context)

        assert result.success is True
        mock_input.assert_not_called()
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is False

    def test_upgrade_missing_preference_prompts(self, tmp_path: Path) -> None:
        """Config exists but no attribution key -> prompts like fresh install."""
        context = _make_context(tmp_path)
        nwave_dir = tmp_path / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "global-config.json"
        # Config exists but no attribution key
        config_file.write_text(
            json.dumps({"rigor": {"level": "standard"}}),
            encoding="utf-8",
        )

        plugin = AttributionPlugin(config_dir=nwave_dir)

        with (
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="y"),
        ):
            mock_stdin.isatty.return_value = True
            result = plugin.install(context)

        assert result.success is True
        config = _read_global_config(nwave_dir)
        assert config["attribution"]["enabled"] is True
        # Rigor key preserved
        assert config["rigor"]["level"] == "standard"


class TestAttributionHookInstallation:
    """Regression tests for hook installation with effective core.hooksPath.

    AC #3: Given a git repo with local core.hooksPath=.git/hooks,
           when install_attribution_hook() runs,
           then the hook is installed in .git/hooks/ (not ~/.nwave/hooks/).

    AC #4: Given a git repo with NO core.hooksPath,
           when install_attribution_hook() runs,
           then the hook is installed in .git/hooks/ (git default)
           and global core.hooksPath is NEVER set.

    AC #5: install_attribution_hook() NEVER sets global core.hooksPath.
    """

    def test_local_hooks_path_takes_precedence(self, tmp_path: Path) -> None:
        """Repo with local core.hooksPath -> hook installed in local hooks dir."""
        # Setup: a git repo with local core.hooksPath
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        local_hooks = repo_dir / ".git" / "hooks"
        local_hooks.mkdir(parents=True)

        nwave_dir = tmp_path / ".nwave"

        # Mock subprocess.run to simulate:
        #   unscoped `git config core.hooksPath` -> local_hooks (effective)
        #   `git config --global core.hooksPath` -> ~/.nwave/hooks/ (shadowed)
        def mock_subprocess_run(cmd, **kwargs):
            from subprocess import CompletedProcess

            cmd_str = " ".join(cmd)
            if cmd_str == "git config core.hooksPath":
                return CompletedProcess(cmd, 0, stdout=str(local_hooks) + "\n")
            if "git config --global core.hooksPath" in cmd_str:
                global_hooks = str(tmp_path / ".nwave" / "hooks")
                return CompletedProcess(cmd, 0, stdout=global_hooks + "\n")
            return CompletedProcess(cmd, 1, stdout="", stderr="")

        with patch(
            "scripts.install.attribution_utils.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            result_path = install_attribution_hook(config_dir=nwave_dir)

        # Hook shim must be in local_hooks, NOT in ~/.nwave/hooks/
        assert result_path.parent == local_hooks
        assert result_path.name == "prepare-commit-msg"
        assert result_path.exists()

    def test_no_hooks_path_installs_to_git_default(self, tmp_path: Path) -> None:
        """No core.hooksPath configured -> hook in .git/hooks/ (git default).

        This is the fix for the core.hooksPath shadowing bug: when no
        hooksPath is configured, nWave must install to .git/hooks/ (where
        git looks by default) instead of creating ~/.nwave/hooks/ and
        overriding core.hooksPath globally (which shadows pre-commit).
        """
        nwave_dir = tmp_path / ".nwave"
        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True)

        # Mock subprocess.run: all git config core.hooksPath calls return not-set.
        # Mock git rev-parse --git-common-dir to return tmp_path/.git (the
        # shared .git directory; worktree-aware sibling of --show-toplevel).
        def mock_subprocess_run(cmd, **kwargs):
            from subprocess import CompletedProcess

            cmd_str = " ".join(cmd)
            if "core.hooksPath" in cmd_str:
                return CompletedProcess(cmd, 1, stdout="", stderr="")
            if "rev-parse --git-common-dir" in cmd_str:
                return CompletedProcess(cmd, 0, stdout=str(tmp_path / ".git") + "\n")
            return CompletedProcess(cmd, 1, stdout="", stderr="")

        with patch(
            "scripts.install.attribution_utils.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            result_path = install_attribution_hook(config_dir=nwave_dir)

        # Hook must be in .git/hooks/ (git default), NOT ~/.nwave/hooks/
        assert result_path.parent == git_hooks
        assert result_path.name == "prepare-commit-msg"
        assert result_path.exists()

    def test_install_never_sets_global_hooks_path(self, tmp_path: Path) -> None:
        """install_attribution_hook() must NEVER call git config --global core.hooksPath.

        Setting global core.hooksPath shadows pre-commit hooks in .git/hooks/.
        This is the root cause of the attribution hook bug.
        """
        nwave_dir = tmp_path / ".nwave"
        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True)

        global_set_calls = []

        def mock_subprocess_run(cmd, **kwargs):
            from subprocess import CompletedProcess

            cmd_str = " ".join(cmd)
            # Detect any attempt to SET global core.hooksPath
            # (5 args: git config --global core.hooksPath <value>)
            if "--global" in cmd_str and "core.hooksPath" in cmd_str and len(cmd) == 5:
                global_set_calls.append(cmd)
                return CompletedProcess(cmd, 0, stdout="", stderr="")
            if "core.hooksPath" in cmd_str:
                return CompletedProcess(cmd, 1, stdout="", stderr="")
            if "rev-parse --git-common-dir" in cmd_str:
                return CompletedProcess(cmd, 0, stdout=str(tmp_path / ".git") + "\n")
            return CompletedProcess(cmd, 1, stdout="", stderr="")

        with patch(
            "scripts.install.attribution_utils.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            install_attribution_hook(config_dir=nwave_dir)

        assert global_set_calls == [], (
            f"install_attribution_hook() must NEVER set global core.hooksPath, "
            f"but called: {global_set_calls}"
        )

    def test_install_succeeds_in_git_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: install_attribution_hook() must work inside a git worktree.

        In a worktree, ``.git`` is a pointer FILE (not a directory) that
        contains ``gitdir: <main-checkout>/.git/worktrees/<name>``. The
        previous resolver used ``git rev-parse --show-toplevel`` and
        appended ``/.git/hooks``, which resolves to ``<worktree>/.git/hooks``
        — but ``<worktree>/.git`` is a file, so the path is invalid and
        the install fails with ``[Errno 20] Not a directory``.

        The fix is to use ``git rev-parse --git-common-dir`` (worktree-aware,
        returns the SHARED ``.git`` directory) and append ``/hooks``. This
        test asserts the fix by setting up a real git worktree with real
        subprocess calls and verifying the install lands in the shared
        ``.git/hooks/`` directory.

        See docs/analysis/rca-attribution-plugin-worktree-isolation.md.
        """
        import subprocess as sp

        # Build a real main-checkout repo so `git rev-parse` actually works
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        sp.run(
            ["git", "init", "-q", "-b", "main", str(main_repo)],
            check=True,
            capture_output=True,
        )
        # An initial commit is required before `git worktree add` can succeed
        sp.run(
            [
                "git",
                "-C",
                str(main_repo),
                "commit",
                "--allow-empty",
                "-q",
                "-m",
                "init",
            ],
            check=True,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )

        # Create a real worktree at tmp_path/wt — git creates the pointer-file
        # `.git` and the per-worktree gitdir under main/.git/worktrees/wt.
        worktree_dir = tmp_path / "wt"
        sp.run(
            [
                "git",
                "-C",
                str(main_repo),
                "worktree",
                "add",
                "-q",
                "-b",
                "feature",
                str(worktree_dir),
            ],
            check=True,
            capture_output=True,
        )

        # Sanity-check: the worktree's `.git` is a FILE (the bug surface).
        assert (worktree_dir / ".git").is_file(), (
            "Worktree setup failed: .git should be a pointer file"
        )

        # cd into the worktree so git rev-parse runs in worktree context.
        monkeypatch.chdir(worktree_dir)

        nwave_dir = tmp_path / ".nwave"

        # No subprocess mocks — exercises the real resolver against a real
        # worktree. This is the test that fails on --show-toplevel and passes
        # with --git-common-dir.
        result_path = install_attribution_hook(config_dir=nwave_dir)

        # The shared hooks dir is <main_repo>/.git/hooks/. That is where the
        # prepare-commit-msg trailer policy belongs (applies to all branches
        # and worktrees) and where --git-common-dir resolves.
        shared_hooks = main_repo / ".git" / "hooks"
        assert result_path.parent == shared_hooks, (
            f"Hook installed in {result_path.parent}, expected {shared_hooks}"
        )
        assert result_path.name == "prepare-commit-msg"
        assert result_path.exists()
        assert result_path.is_file()

    def test_explicit_git_dir_bypasses_git_probing(self, tmp_path: Path) -> None:
        """Passing git_dir=<path> writes to <path>/hooks/ without any git probe.

        Guarantees tests cannot accidentally resolve to the surrounding
        repo's .git/hooks/ even if subprocess.run mocks are incomplete:
        when git_dir is provided, subprocess.run is never called.
        """
        nwave_dir = tmp_path / ".nwave"
        explicit_git = tmp_path / "isolated-repo" / ".git"
        explicit_git.mkdir(parents=True)

        subprocess_calls: list[list[str]] = []

        def fail_on_any_subprocess(cmd, **kwargs):
            subprocess_calls.append(list(cmd))
            raise AssertionError(
                f"git_dir was provided; subprocess.run must not be called, "
                f"but got: {cmd}"
            )

        with patch(
            "scripts.install.attribution_utils.subprocess.run",
            side_effect=fail_on_any_subprocess,
        ):
            result_path = install_attribution_hook(
                config_dir=nwave_dir,
                git_dir=explicit_git,
            )

        assert subprocess_calls == []
        assert result_path.parent == explicit_git / "hooks"
        assert result_path.name == "prepare-commit-msg"
        assert result_path.exists()
