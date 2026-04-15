"""Tests for scripts/shared/install_paths.py -- centralized path constants."""

import sys
from pathlib import Path

from scripts.shared.install_paths import (
    AGENTS_SUBDIR,
    COMMANDS_LEGACY_SUBDIR,
    DES_LIB_SUBDIR,
    MANIFEST_FILENAME,
    SKILLS_SUBDIR,
    TEMPLATES_SUBDIR,
    agents_dir,
    des_dir,
    manifest_path,
    skills_dir,
    templates_dir,
)


class TestPathConstants:
    """Test that path constants match the expected installation layout."""

    def test_agents_subdir(self):
        assert Path("agents") / "nw" == AGENTS_SUBDIR

    def test_skills_subdir(self):
        assert Path("skills") == SKILLS_SUBDIR

    def test_templates_subdir(self):
        assert Path("templates") == TEMPLATES_SUBDIR

    def test_des_lib_subdir(self):
        assert Path("lib") / "python" / "des" == DES_LIB_SUBDIR

    def test_commands_legacy_subdir(self):
        assert Path("commands") / "nw" == COMMANDS_LEGACY_SUBDIR

    def test_manifest_filename(self):
        assert MANIFEST_FILENAME == "nwave-manifest.txt"


class TestPathHelpers:
    """Test path helper functions produce correct absolute paths."""

    def test_agents_dir(self, tmp_path):
        result = agents_dir(tmp_path)
        assert result == tmp_path / "agents" / "nw"

    def test_skills_dir(self, tmp_path):
        result = skills_dir(tmp_path)
        assert result == tmp_path / "skills"

    def test_templates_dir(self, tmp_path):
        result = templates_dir(tmp_path)
        assert result == tmp_path / "templates"

    def test_des_dir(self, tmp_path):
        result = des_dir(tmp_path)
        assert result == tmp_path / "lib" / "python" / "des"

    def test_manifest_path(self, tmp_path):
        result = manifest_path(tmp_path)
        assert result == tmp_path / "nwave-manifest.txt"

    def test_paths_consistent_with_verifier_expectations(self, tmp_path):
        """Path helpers produce paths matching InstallationVerifier conventions."""
        claude = tmp_path / ".claude"
        assert agents_dir(claude) == claude / "agents" / "nw"
        assert skills_dir(claude) == claude / "skills"
        assert des_dir(claude) == claude / "lib" / "python" / "des"
        assert manifest_path(claude) == claude / "nwave-manifest.txt"


class TestResolvePythonCommandForSpawn:
    """Tests for resolve_python_command_for_spawn() -- non-shell context.

    Consumers pass the result to Bun.spawn / subprocess without shell=True,
    so no shell variable expansion happens. Paths must be absolute and
    forward-slash-normalized so they embed safely into TypeScript
    double-quoted string literals without triggering escape sequences.
    """

    def test_linux_path_returned_unchanged(self, monkeypatch):
        from scripts.shared.install_paths import resolve_python_command_for_spawn

        monkeypatch.setattr(
            sys,
            "executable",
            "/home/alex/.local/share/pipx/venvs/nwave-ai/bin/python",
        )
        result = resolve_python_command_for_spawn()
        assert "$HOME" not in result
        assert "\\" not in result
        assert result == "/home/alex/.local/share/pipx/venvs/nwave-ai/bin/python"

    def test_windows_path_normalized_to_forward_slash(self, monkeypatch):
        from scripts.shared.install_paths import resolve_python_command_for_spawn

        monkeypatch.setattr(
            sys,
            "executable",
            r"C:\Users\tester\pipx\venvs\nwave-ai\Scripts\python.exe",
        )
        result = resolve_python_command_for_spawn()
        assert "\\" not in result
        assert result == "C:/Users/tester/pipx/venvs/nwave-ai/Scripts/python.exe"

    def test_linux_venv_fallback(self, monkeypatch):
        from scripts.shared.install_paths import resolve_python_command_for_spawn

        monkeypatch.setattr(sys, "executable", "/home/alex/project/.venv/bin/python3")
        assert resolve_python_command_for_spawn() == "python3"

    def test_windows_venv_fallback(self, monkeypatch):
        from scripts.shared.install_paths import resolve_python_command_for_spawn

        monkeypatch.setattr(
            sys,
            "executable",
            r"C:\Users\tester\project\.venv\Scripts\python.exe",
        )
        assert resolve_python_command_for_spawn() == "python3"


class TestResolveDesLibPathForSpawn:
    """Tests for resolve_des_lib_path_for_spawn() -- non-shell context."""

    def test_returns_forward_slash_absolute_path(self, monkeypatch, tmp_path):
        import scripts.shared.install_paths as ip

        fake_home = tmp_path / "fake-home"
        fake_home.mkdir()
        monkeypatch.setattr(ip.Path, "home", lambda: fake_home)

        result = ip.resolve_des_lib_path_for_spawn()
        assert "$HOME" not in result
        assert "\\" not in result
        assert result.endswith("/.claude/lib/python")
