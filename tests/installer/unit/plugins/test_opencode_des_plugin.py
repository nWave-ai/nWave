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
"""

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

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


class TestFreshInstallCreatesShimAndManifest:
    """Test that install() creates shim file and manifest on fresh install."""

    def test_fresh_install_creates_shim_and_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: OpenCode is detected and DES module is installed and no prior shim exists
        WHEN: install() is called
        THEN: nwave-des.ts exists in plugins dir and manifest exists
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

        plugin = OpenCodeDESPlugin()
        result = plugin.install(context)

        assert result.success is True
        assert (plugins_dir / "nwave-des.ts").exists()
        assert (opencode_dir / ".nwave-des-manifest.json").exists()


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
        THEN: The shim file contains the resolved Python path and PYTHONPATH
        """
        context, opencode_dir, plugins_dir = _make_context(tmp_path)
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

        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        shim_content = (plugins_dir / "nwave-des.ts").read_text(encoding="utf-8")
        assert "/home/tester/.local/bin/python3" in shim_content
        assert "/home/tester/.claude/lib/python" in shim_content
        assert "$HOME" not in shim_content
        assert "{{PYTHON_PATH}}" not in shim_content
        assert "{{PYTHONPATH}}" not in shim_content


class TestManifestContainsVersionAndHash:
    """Test that manifest records version and content hash."""

    def test_manifest_contains_version_and_hash(self, tmp_path, monkeypatch):
        """
        GIVEN: A fresh install
        WHEN: install() completes
        THEN: Manifest contains version and sha256 hash of the shim
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

        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        manifest_path = opencode_dir / ".nwave-des-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert "version" in manifest
        assert "sha256" in manifest
        assert "shim_file" in manifest

        # Verify hash matches actual file content
        shim_content = (plugins_dir / "nwave-des.ts").read_bytes()
        expected_hash = hashlib.sha256(shim_content).hexdigest()
        assert manifest["sha256"] == expected_hash


class TestReinstallOverwritesExistingShim:
    """Test that reinstall overwrites existing shim without errors."""

    def test_reinstall_overwrites_existing_shim(self, tmp_path, monkeypatch):
        """
        GIVEN: A prior installation with version 1.0.0
        WHEN: install() runs again with a new template
        THEN: The shim is overwritten and manifest is updated
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

        # First install
        plugin = OpenCodeDESPlugin()
        plugin.install(context)

        first_content = (plugins_dir / "nwave-des.ts").read_text(encoding="utf-8")

        # Modify template to simulate version change
        templates_dir = context.framework_source / "templates"
        (templates_dir / "opencode-des-plugin.ts.template").write_text(
            "// Python: {{PYTHON_PATH}}\n"
            "// PYTHONPATH: {{PYTHONPATH}}\n"
            "// Version 2.0\n"
            "export default function nwaveDES() { return {}; }\n",
            encoding="utf-8",
        )

        # Second install
        result = plugin.install(context)

        assert result.success is True
        second_content = (plugins_dir / "nwave-des.ts").read_text(encoding="utf-8")
        assert second_content != first_content
        assert "Version 2.0" in second_content


class TestUninstallRemovesShimAndManifest:
    """Test that uninstall removes shim and manifest only."""

    def test_uninstall_removes_shim_and_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: A prior installation left the shim and manifest
        WHEN: uninstall() is called
        THEN: The shim and manifest are removed and other user plugins are untouched
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

        # Uninstall
        result = plugin.uninstall(context)

        assert result.success is True
        assert not (plugins_dir / "nwave-des.ts").exists()
        assert not (opencode_dir / ".nwave-des-manifest.json").exists()
        assert user_plugin.exists(), "User plugin must remain untouched"


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
        THEN: no occurrence of '$HOME' appears in the rendered content
        """
        context, opencode_dir, plugins_dir = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_des_plugin._opencode_config_dir",
            lambda: opencode_dir,
        )

        plugin = OpenCodeDESPlugin()
        result = plugin.install(context)
        assert result.success is True

        shim_content = (plugins_dir / "nwave-des.ts").read_text(encoding="utf-8")
        assert "$HOME" not in shim_content, (
            f"Rendered shim contains '$HOME' literal -- will fail in "
            f"Bun.spawn. Shim content:\n{shim_content}"
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
