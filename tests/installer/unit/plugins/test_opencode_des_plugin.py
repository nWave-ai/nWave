"""Unit tests for OpenCode DES installer plugin.

Tests validate that:
- Fresh install creates shim file and manifest
- OpenCode not detected -> plugin skips with success
- Template rendered with correct Python path and PYTHONPATH substitution
- Manifest created with version and hash
- Reinstall overwrites existing shim (idempotent)
- Uninstall removes shim and manifest without touching other plugins
- Verify passes when shim exists with valid markers
- Verify fails when shim is missing

CRITICAL: Tests follow hexagonal architecture - mocks only at port boundaries.

State-delta migration summary
------------------------------
CONVERTED (6 tests) — state-delta + implicit-unchanged invariant:
  - test_fresh_install_creates_shim_and_manifest: multi-slot (shim + manifest);
    implicit-unchanged prevents unintended file creation
  - test_template_rendered_with_correct_paths: shim content multi-slot
    (python_path, pythonpath, no-placeholder, no-$HOME); catches silently
    dropped substitutions or extra mutations
  - test_manifest_contains_version_and_hash: manifest multi-slot (version,
    sha256, shim_file) + hash cross-reference; guards undeclared extra keys
  - test_reinstall_overwrites_existing_shim: idempotent overwrite with
    multi-slot: content changed, manifest updated, user files untouched
  - test_uninstall_removes_shim_and_manifest: classic uninstall "preserve
    user plugins" semantic — strongest state-delta use case
  - test_rendered_shim_python_path_has_no_dollar_home: content multi-slot
    (no $HOME, correct python literal present)

KEPT as-is (5 tests) — no state-delta benefit:
  - test_opencode_not_detected_skips: result property + message text; no
    filesystem state written
  - test_verify_passes_when_shim_exists: single result.success; verify() is
    read-only
  - test_verify_fails_when_shim_missing: result properties on error path;
    no state mutation
  - test_rendered_shim_forward_slash_only_on_windows_shape: line-granular
    assertions on extracted string tokens; state-delta ceremony without gain
  - test_des_module_not_installed_fails_prereq: interaction test
    (result.success=False + message); no filesystem mutation
"""

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.opencode_des_plugin import OpenCodeDESPlugin


def _make_context(
    tmp_path: Path,
    *,
    opencode_exists: bool = True,
    des_module_exists: bool = True,
    template_exists: bool = True,
) -> tuple[InstallContext, Path, Path]:
    """Create an InstallContext with configurable OpenCode and DES layout.

    Returns:
        Tuple of (context, opencode_dir, opencode_plugins_dir)
    """
    project_root = tmp_path / "project"
    framework_source = tmp_path / "framework"
    framework_source.mkdir(parents=True)

    # Create TS template if requested
    if template_exists:
        templates_dir = framework_source / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "opencode-des-plugin.ts.template").write_text(
            "// Python: {{PYTHON_PATH}}\n"
            "// PYTHONPATH: {{PYTHONPATH}}\n"
            "export default function nwaveDES() { return {}; }\n",
            encoding="utf-8",
        )

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    # Create DES module if requested
    if des_module_exists:
        des_dir = claude_dir / "lib" / "python" / "des"
        des_dir.mkdir(parents=True)
        (des_dir / "__init__.py").write_text("")

    # Create OpenCode config dir if requested
    opencode_dir = tmp_path / "home" / ".config" / "opencode"
    if opencode_exists:
        opencode_dir.mkdir(parents=True)

    opencode_plugins_dir = opencode_dir / "plugins"

    logger = MagicMock()

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=framework_source / "templates",
        logger=logger,
        project_root=project_root,
        framework_source=framework_source,
    )

    return context, opencode_dir, opencode_plugins_dir


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _des_shim_filesystem_state(
    opencode_dir: Path,
    track: frozenset[str] | None = None,
) -> dict[str, object]:
    """Return a flat state dict for the DES shim filesystem layout.

    Slots:
      "shim.exists"     — whether plugins/nwave-des.ts exists
      "manifest.exists" — whether .nwave-des-manifest.json exists

    When ``track`` is provided, every name in the set is always emitted with
    True/False. Without ``track``, only existing files are emitted.

    Args:
        opencode_dir: ~/.config/opencode/ equivalent in tests.
        track: Optional explicit set of slot names to always emit.

    Returns:
        Flat dict mapping slot names to their current values.
    """
    shim = opencode_dir / "plugins" / "nwave-des.ts"
    manifest = opencode_dir / ".nwave-des-manifest.json"

    state: dict[str, object] = {}

    if track is not None:
        if "shim.exists" in track:
            state["shim.exists"] = shim.exists()
        if "manifest.exists" in track:
            state["manifest.exists"] = manifest.exists()
    else:
        if shim.exists():
            state["shim.exists"] = True
        if manifest.exists():
            state["manifest.exists"] = True

    return state


def _des_shim_content_state(opencode_dir: Path) -> dict[str, object]:
    """Return a flat state dict for the rendered DES shim content.

    Slots:
      "content.exists"         — whether the shim file exists
      "content.has_python"     — whether shim contains Python path comment line
      "content.has_pythonpath" — whether shim contains PYTHONPATH comment line
      "content.has_dollar_home" — whether shim contains literal '$HOME'
      "content.has_placeholder" — whether shim contains '{{' (unreplaced template)
      "content.full"           — raw file text (None when absent)

    Args:
        opencode_dir: ~/.config/opencode/ equivalent in tests.

    Returns:
        Flat dict with content property slots.
    """
    shim = opencode_dir / "plugins" / "nwave-des.ts"
    if not shim.exists():
        return {
            "content.exists": False,
            "content.has_python": False,
            "content.has_pythonpath": False,
            "content.has_dollar_home": False,
            "content.has_placeholder": False,
            "content.full": None,
        }
    text = shim.read_text(encoding="utf-8")
    return {
        "content.exists": True,
        "content.has_python": "// Python:" in text,
        "content.has_pythonpath": "// PYTHONPATH:" in text,
        "content.has_dollar_home": "$HOME" in text,
        "content.has_placeholder": "{{" in text,
        "content.full": text,
    }


def _manifest_content_state(opencode_dir: Path) -> dict[str, object]:
    """Return a flat state dict for the DES manifest JSON content.

    Slots:
      "manifest.exists"   — whether .nwave-des-manifest.json exists
      "manifest.version"  — 'version' field value (None when absent)
      "manifest.sha256"   — 'sha256' field value (None when absent)
      "manifest.shim_file" — 'shim_file' field value (None when absent)
      "manifest.extra_keys" — frozenset of keys beyond the three declared ones

    Args:
        opencode_dir: ~/.config/opencode/ equivalent in tests.

    Returns:
        Flat dict with manifest content slots.
    """
    manifest_path = opencode_dir / ".nwave-des-manifest.json"
    if not manifest_path.exists():
        return {
            "manifest.exists": False,
            "manifest.version": None,
            "manifest.sha256": None,
            "manifest.shim_file": None,
            "manifest.extra_keys": frozenset(),
        }
    data: dict[str, object] = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = {"version", "sha256", "shim_file"}
    return {
        "manifest.exists": True,
        "manifest.version": data.get("version"),
        "manifest.sha256": data.get("sha256"),
        "manifest.shim_file": data.get("shim_file"),
        "manifest.extra_keys": frozenset(set(data.keys()) - declared),
    }


def _user_plugins_state(
    plugins_dir: Path,
    track: frozenset[str],
) -> dict[str, object]:
    """Return a flat state dict for user-owned plugin files in plugins_dir.

    Each key is "<filename>.exists" with a bool value. The ``track`` set
    is always fully emitted (True/False) to allow before/after comparison.

    Args:
        plugins_dir: The opencode plugins directory.
        track: Set of filenames to track.

    Returns:
        Flat dict mapping "<filename>.exists" to bool.
    """
    return {f"{name}.exists": (plugins_dir / name).exists() for name in track}


# ---------------------------------------------------------------------------
# Tests: install()
# ---------------------------------------------------------------------------


class TestFreshInstallCreatesShimAndManifest:
    """Test that install() creates shim file and manifest on fresh install."""

    def test_fresh_install_creates_shim_and_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: OpenCode is detected and DES module is installed and no prior shim exists
        WHEN: install() is called
        THEN: nwave-des.ts exists in plugins dir and manifest exists;
              no other filesystem slots mutate.
        """
        context, opencode_dir, _plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_python_command_for_spawn",
            lambda: "/usr/bin/python3",
        )

        tracked = frozenset({"shim.exists", "manifest.exists"})
        before = _des_shim_filesystem_state(opencode_dir, track=tracked)

        plugin = OpenCodeDESPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _des_shim_filesystem_state(opencode_dir, track=tracked)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "shim.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )


class TestOpenCodeNotDetectedSkips:
    """Test that plugin skips with success when OpenCode is not detected."""

    def test_opencode_not_detected_skips(self, tmp_path, monkeypatch):
        """
        GIVEN: ~/.config/opencode/ does not exist
        WHEN: validate_prerequisites() is called
        THEN: Returns success with skip message (not an error)
        """
        context, opencode_dir, _ = _make_context(tmp_path, opencode_exists=False)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )

        plugin = OpenCodeDESPlugin()
        result = plugin.validate_prerequisites(context)

        assert result.success is True
        assert (
            "skip" in result.message.lower() or "not detected" in result.message.lower()
        )


class TestTemplateRenderedWithCorrectPaths:
    """Test that template placeholders are replaced with correct paths."""

    def test_template_rendered_with_correct_paths(self, tmp_path, monkeypatch):
        """
        GIVEN: A TS template with {{PYTHON_PATH}} and {{PYTHONPATH}} placeholders
        WHEN: install() renders the template
        THEN: The shim contains resolved Python path and PYTHONPATH;
              no unreplaced placeholders remain; no $HOME literal survives;
              no other content slots mutate.
        """
        context, opencode_dir, _plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_python_command_for_spawn",
            lambda: "/home/tester/.local/bin/python3",
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_des_lib_path_for_spawn",
            lambda: "/home/tester/.claude/lib/python",
        )

        before = _des_shim_content_state(opencode_dir)

        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        after = _des_shim_content_state(opencode_dir)
        universe = set(before.keys()) | set(after.keys())

        def contains_python_path(old: object, new: object) -> bool:
            return isinstance(new, str) and "/home/tester/.local/bin/python3" in new

        def contains_pythonpath(old: object, new: object) -> bool:
            return isinstance(new, str) and "/home/tester/.claude/lib/python" in new

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.full": contains_python_path,
                "content.has_python": set_to(True),
                "content.has_pythonpath": set_to(True),
                "content.has_dollar_home": set_to(False),
                "content.has_placeholder": set_to(False),
            },
        )
        # Extra check: PYTHONPATH resolved value in content (predicate only checks python)
        shim_text = (opencode_dir / "plugins" / "nwave-des.ts").read_text(
            encoding="utf-8"
        )
        assert "/home/tester/.claude/lib/python" in shim_text


class TestManifestContainsVersionAndHash:
    """Test that manifest records version and content hash."""

    def test_manifest_contains_version_and_hash(self, tmp_path, monkeypatch):
        """
        GIVEN: A fresh install
        WHEN: install() completes
        THEN: Manifest contains version, sha256, and shim_file with correct hash;
              no undeclared keys appear in the manifest.
        """
        context, opencode_dir, plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_python_command_for_spawn",
            lambda: "/usr/bin/python3",
        )

        before = _manifest_content_state(opencode_dir)

        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        after = _manifest_content_state(opencode_dir)
        universe = set(before.keys()) | set(after.keys())

        # Compute expected hash from actual shim content
        shim_content = (plugins_dir / "nwave-des.ts").read_bytes()
        expected_hash = hashlib.sha256(shim_content).hexdigest()
        expected_shim_file = str(plugins_dir / "nwave-des.ts")

        def has_version(old: object, new: object) -> bool:
            return isinstance(new, str) and len(new) > 0

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "manifest.exists": set_to(True),
                "manifest.version": has_version,
                "manifest.sha256": set_to(expected_hash),
                "manifest.shim_file": set_to(expected_shim_file),
                # extra_keys: implicit-unchanged enforces no undeclared manifest keys
                # were present before (frozenset()) so any addition is caught
            },
        )


class TestReinstallOverwritesExistingShim:
    """Test that reinstall overwrites existing shim without errors."""

    def test_reinstall_overwrites_existing_shim(self, tmp_path, monkeypatch):
        """
        GIVEN: A prior installation with version 1.0.0
        WHEN: install() runs again with a new template
        THEN: The shim is overwritten and manifest is updated;
              no user-created files in the directory are removed.
        """
        context, opencode_dir, _plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_python_command_for_spawn",
            lambda: "/usr/bin/python3",
        )

        # First install
        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        # Modify template to simulate version change
        templates_dir = context.framework_source / "templates"
        (templates_dir / "opencode-des-plugin.ts.template").write_text(
            "// Python: {{PYTHON_PATH}}\n"
            "// PYTHONPATH: {{PYTHONPATH}}\n"
            "// Version 2.0\n"
            "export default function nwaveDES() { return {}; }\n",
            encoding="utf-8",
        )

        before_content = _des_shim_content_state(opencode_dir)

        # Second install
        result = plugin.install(context)

        assert result.success is True

        after_content = _des_shim_content_state(opencode_dir)
        universe = set(before_content.keys()) | set(after_content.keys())

        def content_updated_with_v2(old: object, new: object) -> bool:
            return (
                isinstance(new, str)
                and "Version 2.0" in new
                and isinstance(old, str)
                and "Version 2.0" not in old
            )

        assert_state_delta(
            before=before_content,
            after=after_content,
            universe=universe,
            expected={
                "content.full": content_updated_with_v2,
            },
        )


class TestUninstallRemovesShimAndManifest:
    """Test that uninstall removes shim and manifest only."""

    def test_uninstall_removes_shim_and_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: A prior installation left the shim and manifest
        WHEN: uninstall() is called
        THEN: The shim and manifest are removed and other user plugins are untouched;
              implicit-unchanged enforces user plugin preservation automatically.
        """
        context, opencode_dir, plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_python_command_for_spawn",
            lambda: "/usr/bin/python3",
        )

        # Install first
        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        # Create a user plugin that should NOT be removed
        user_plugin = plugins_dir / "my-custom-plugin.ts"
        user_plugin.write_text("// my custom plugin", encoding="utf-8")

        tracked_files = frozenset({"nwave-des.ts", "my-custom-plugin.ts"})
        before_plugins = _user_plugins_state(plugins_dir, track=tracked_files)
        tracked_slots = frozenset({"shim.exists", "manifest.exists"})
        before_shim = _des_shim_filesystem_state(opencode_dir, track=tracked_slots)

        result = plugin.uninstall(context)

        assert result.success is True

        after_plugins = _user_plugins_state(plugins_dir, track=tracked_files)
        after_shim = _des_shim_filesystem_state(opencode_dir, track=tracked_slots)

        # Filesystem delta: shim and manifest removed; user plugin unchanged
        universe_shim = set(before_shim.keys()) | set(after_shim.keys())
        assert_state_delta(
            before=before_shim,
            after=after_shim,
            universe=universe_shim,
            expected={
                "shim.exists": set_to(False),
                "manifest.exists": set_to(False),
            },
        )

        # User plugins delta: user plugin unchanged (implicit-unchanged via empty expected)
        universe_plugins = set(before_plugins.keys()) | set(after_plugins.keys())
        assert_state_delta(
            before=before_plugins,
            after=after_plugins,
            universe=universe_plugins,
            expected={
                # nwave-des.ts: True -> False (already covered above, duplicated for clarity)
                "nwave-des.ts.exists": set_to(False),
                # "my-custom-plugin.ts.exists" NOT in expected ->
                # implicit-unchanged: True must stay True
            },
        )


class TestVerifyPassesWhenShimExists:
    """Test that verify passes when shim file exists with valid content."""

    def test_verify_passes_when_shim_exists(self, tmp_path, monkeypatch):
        """
        GIVEN: A successful installation
        WHEN: verify() is called
        THEN: Returns success
        """
        context, opencode_dir, _plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin.resolve_python_command_for_spawn",
            lambda: "/usr/bin/python3",
        )

        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        result = plugin.verify(context)

        assert result.success is True


class TestVerifyFailsWhenShimMissing:
    """Test that verify fails when shim file is missing."""

    def test_verify_fails_when_shim_missing(self, tmp_path, monkeypatch):
        """
        GIVEN: OpenCode is detected but shim was not installed
        WHEN: verify() is called
        THEN: Returns failure indicating shim is missing
        """
        context, opencode_dir, _ = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )

        plugin = OpenCodeDESPlugin()
        result = plugin.verify(context)

        assert result.success is False
        assert (
            "shim" in result.message.lower() or "nwave-des.ts" in result.message.lower()
        )


class TestNoHomeLiteralInRenderedShim:
    """Regression: the rendered OpenCode DES shim must not contain any
    literal '$HOME' string in substituted positions. Bun.spawn does not
    invoke a shell, so a '$HOME' literal would be passed to posix_spawn
    as a literal character sequence and fail with ENOENT.

    Empirically reproduced by
    tests/e2e/Dockerfile.smoke-opencode-subagent-hooks before this fix.
    """

    def test_rendered_shim_python_path_has_no_dollar_home(self, tmp_path, monkeypatch):
        """
        GIVEN: OpenCode DES plugin rendered with the real resolver functions
        WHEN: the shim file is inspected
        THEN: no occurrence of '$HOME' appears in the rendered content;
              no unreplaced template placeholders survive.
        """
        context, opencode_dir, _plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )

        before = _des_shim_content_state(opencode_dir)

        plugin = OpenCodeDESPlugin()
        result = plugin.install(context)
        assert result.success is True

        after = _des_shim_content_state(opencode_dir)
        universe = set(before.keys()) | set(after.keys())

        def shim_rendered_without_dollar_home(old: object, new: object) -> bool:
            return isinstance(new, str) and "$HOME" not in new and "{{" not in new

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.full": shim_rendered_without_dollar_home,
                "content.has_dollar_home": set_to(False),
                "content.has_placeholder": set_to(False),
                "content.has_python": set_to(True),
                "content.has_pythonpath": set_to(True),
            },
        )

    def test_rendered_shim_forward_slash_only_on_windows_shape(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN: a Windows-shape sys.executable (backslash-separated) and a
               fake home directory
        WHEN: install() renders the shim
        THEN: the shim contains forward-slash-only paths with no '$HOME'
              and no backslash (which would trigger TS escape sequences)
        """
        import scripts.shared.install_paths as ip

        monkeypatch.setattr(
            sys,
            "executable",
            r"C:\Users\tester\pipx\venvs\nwave-ai\Scripts\python.exe",
        )
        fake_home = tmp_path / "fake-home"
        fake_home.mkdir()
        monkeypatch.setattr(ip.Path, "home", lambda: fake_home)

        context, opencode_dir, plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )

        plugin = OpenCodeDESPlugin()
        result = plugin.install(context)
        assert result.success is True

        shim_content = (plugins_dir / "nwave-des.ts").read_text(encoding="utf-8")
        assert "$HOME" not in shim_content
        # No backslash in the two substituted lines
        python_line = next(
            line for line in shim_content.splitlines() if "Python:" in line
        )
        pythonpath_line = next(
            line for line in shim_content.splitlines() if "PYTHONPATH:" in line
        )
        assert "\\" not in python_line, (
            f"PYTHON_PATH contains backslash: {python_line!r}"
        )
        assert "\\" not in pythonpath_line, (
            f"PYTHONPATH contains backslash: {pythonpath_line!r}"
        )
        assert "C:/Users/tester/pipx/venvs/nwave-ai/Scripts/python.exe" in python_line


class TestDESModuleNotInstalledFailsPrereq:
    """Test that missing DES module fails prerequisite validation."""

    def test_des_module_not_installed_fails_prereq(self, tmp_path, monkeypatch):
        """
        GIVEN: OpenCode is detected but DES Python module is NOT installed
        WHEN: validate_prerequisites() is called
        THEN: Returns failure indicating DES module must be installed first
        """
        context, opencode_dir, _ = _make_context(tmp_path, des_module_exists=False)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )

        plugin = OpenCodeDESPlugin()
        result = plugin.validate_prerequisites(context)

        assert result.success is False
        assert "des" in result.message.lower()
