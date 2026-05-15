"""Unit tests for Codex CLI skills installer plugin.

Tests validate that:
- validate_prerequisites() skips gracefully when Codex CLI is not detected
- validate_prerequisites() proceeds when Codex CLI directory exists
- install() copies SKILL.md files into $HOME/.agents/skills/{name}/SKILL.md
- install() strips Claude Code-only frontmatter fields
- install() writes a manifest tracking installed skill names
- verify() returns success after a successful install
- uninstall() removes only nWave-installed skills, preserving user-created ones

Tests follow hexagonal architecture - mocks only at port boundaries.

State-delta paradigm: install / uninstall mutate multiple filesystem slots
(per-skill directory presence, manifest presence, content fields). The
multi-slot tests below use ``assert_state_delta`` so implicit-unchanged
catches any unintended sibling mutations.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.codex_skills_plugin import CodexSkillsPlugin


if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_context(
    tmp_path: Path,
    *,
    skills: dict[str, str] | None = None,
    public_agents_yaml: str | None = None,
) -> tuple[InstallContext, Path, Path]:
    """Create an InstallContext with a flat-layout skills source.

    Args:
        tmp_path: Pytest temp directory
        skills: Optional mapping of skill_name -> SKILL.md content. Defaults
            to a single ``nw-test-skill`` with minimal frontmatter.
        public_agents_yaml: Optional framework-catalog.yaml content. When None,
            dev_mode is set to True so all skills are treated as installable.

    Returns:
        Tuple of (context, project_root, framework_source).
    """
    project_root = tmp_path / "project"
    framework_source = project_root / "nWave"
    framework_source.mkdir(parents=True)

    skills_dir = framework_source / "skills"
    skills_dir.mkdir()

    if skills is None:
        skills = {
            "nw-test-skill": (
                "---\n"
                "name: nw-test-skill\n"
                "description: A test skill\n"
                "user-invocable: false\n"
                "disable-model-invocation: true\n"
                "---\n\n"
                "# Test Skill Body\n"
            )
        }

    for skill_name, content in skills.items():
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    # Empty agents directory so build_ownership_map returns {}
    (framework_source / "agents").mkdir()

    if public_agents_yaml is not None:
        (framework_source / "framework-catalog.yaml").write_text(
            public_agents_yaml, encoding="utf-8"
        )

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts",
        templates_dir=framework_source / "templates",
        logger=MagicMock(),
        project_root=project_root,
        framework_source=framework_source,
        dev_mode=True,  # bypass public-agent filtering
    )
    return context, project_root, framework_source


def _patch_codex_dirs(monkeypatch, codex_skills_dir: Path, codex_config_dir: Path):
    """Redirect _codex_skills_dir() and _codex_config_dir() to tmp paths."""
    monkeypatch.setattr(
        "scripts.install.plugins.codex_skills_plugin._codex_skills_dir",
        lambda: codex_skills_dir,
    )
    monkeypatch.setattr(
        "scripts.install.plugins.codex_skills_plugin._codex_config_dir",
        lambda: codex_config_dir,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCodexSkillsDirSemantics:
    """_codex_skills_dir: production path uses HOME; NWAVE_AGENTS_HOME overrides for tests."""

    def test_production_path_ignores_codex_home(self, monkeypatch):
        """
        GIVEN: CODEX_HOME is set to an arbitrary directory
        WHEN: _codex_skills_dir() is called
        THEN: The returned path is under the real HOME, NOT derived from CODEX_HOME.
              (CODEX_HOME only overrides ~/.codex/; skills are always under $HOME/.agents/)
        """
        # bypass: single-property assertion — no state mutation, no delta needed
        from pathlib import Path

        from scripts.install.plugins.codex_skills_plugin import _codex_skills_dir

        monkeypatch.setenv("CODEX_HOME", "/tmp/custom-codex-home")
        # NWAVE_AGENTS_HOME must be absent so we exercise the pure HOME branch
        monkeypatch.delenv("NWAVE_AGENTS_HOME", raising=False)

        result = _codex_skills_dir()

        expected = Path.home() / ".agents" / "skills"
        assert result == expected, (
            "CODEX_HOME must not influence the skills path — "
            "skills are always $HOME/.agents/skills/"
        )

    def test_nwave_agents_home_overrides_home_for_tests(self, monkeypatch, tmp_path):
        """
        GIVEN: NWAVE_AGENTS_HOME is set to a tmp directory
        WHEN: _codex_skills_dir() is called
        THEN: The returned path is under NWAVE_AGENTS_HOME (test isolation override)
        """
        # bypass: single-property assertion
        from scripts.install.plugins.codex_skills_plugin import _codex_skills_dir

        monkeypatch.setenv("NWAVE_AGENTS_HOME", str(tmp_path))
        monkeypatch.delenv("CODEX_HOME", raising=False)

        result = _codex_skills_dir()

        assert result == tmp_path / ".agents" / "skills"


class TestValidatePrerequisites:
    """validate_prerequisites: skip vs proceed based on Codex detection."""

    def test_skips_gracefully_when_codex_not_detected(self, tmp_path, monkeypatch):
        """
        GIVEN: ~/.codex/ does not exist AND `codex` binary is not in PATH
        WHEN: validate_prerequisites() is called
        THEN: Returns success with skip message (NOT an error)
        """
        context, _, _ = _make_context(tmp_path)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"  # does NOT exist
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)
        # Force shutil.which("codex") -> None inside the plugin module namespace
        monkeypatch.setattr(
            "scripts.install.plugins.codex_skills_plugin.shutil.which",
            lambda _name: None,
        )

        plugin = CodexSkillsPlugin()
        result = plugin.validate_prerequisites(context)

        assert result.success is True
        assert (
            "skip" in result.message.lower() or "not detected" in result.message.lower()
        )

    def test_proceeds_when_codex_config_dir_exists(self, tmp_path, monkeypatch):
        """
        GIVEN: ~/.codex/ exists
        WHEN: validate_prerequisites() is called
        THEN: Returns success with non-skip message
        """
        context, _, _ = _make_context(tmp_path)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)

        plugin = CodexSkillsPlugin()
        result = plugin.validate_prerequisites(context)

        assert result.success is True
        assert "validated" in result.message.lower()


class TestInstallCopiesSkills:
    """install: copies SKILL.md files into the Codex skills directory."""

    def test_install_creates_skill_directory_and_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: A flat-layout source with one skill (nw-test-skill)
            AND ~/.codex/ exists (Codex detected)
        WHEN: install() runs
        THEN: $HOME/.agents/skills/nw-test-skill/SKILL.md exists AND
              the manifest exists, while no other slots are mutated.
        """
        context, _, _ = _make_context(tmp_path)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)

        # Capture before-state (target tree empty)
        tracked_keys = {
            "nw-test-skill.exists",
            "manifest.exists",
            "stranger-skill.exists",  # never created
        }

        def snapshot() -> dict[str, object]:
            return {
                "nw-test-skill.exists": (
                    codex_skills_dir / "nw-test-skill" / "SKILL.md"
                ).is_file(),
                "manifest.exists": (
                    codex_skills_dir / ".nwave-manifest.json"
                ).is_file(),
                "stranger-skill.exists": (
                    codex_skills_dir / "stranger-skill" / "SKILL.md"
                ).is_file(),
            }

        before = snapshot()

        plugin = CodexSkillsPlugin()
        result = plugin.install(context)

        after = snapshot()

        assert result.success is True
        assert_state_delta(
            before,
            after,
            universe=tracked_keys,
            expected={
                "nw-test-skill.exists": set_to(True),
                "manifest.exists": set_to(True),
                # stranger-skill.exists must remain False (implicit-unchanged)
            },
        )

    def test_install_strips_forbidden_frontmatter_fields(self, tmp_path, monkeypatch):
        """
        GIVEN: A source SKILL.md with `user-invocable` and
               `disable-model-invocation` fields in frontmatter
        WHEN: install() copies the skill
        THEN: The installed SKILL.md does NOT contain those fields,
              but retains name, description, and body.
        """
        context, _, _ = _make_context(tmp_path)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)

        plugin = CodexSkillsPlugin()
        result = plugin.install(context)
        assert result.success is True

        content = (codex_skills_dir / "nw-test-skill" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        # Forbidden fields stripped
        assert "user-invocable" not in content
        assert "disable-model-invocation" not in content
        # Essential fields preserved
        assert "name: nw-test-skill" in content
        assert "description: A test skill" in content
        assert "# Test Skill Body" in content

    def test_install_manifest_records_installed_names(self, tmp_path, monkeypatch):
        """
        GIVEN: Two skills in source (nw-alpha, nw-beta)
        WHEN: install() runs
        THEN: The manifest's installed_skills list contains both names sorted
        """
        skills = {
            "nw-alpha": "---\nname: nw-alpha\ndescription: a\n---\nbody-a\n",
            "nw-beta": "---\nname: nw-beta\ndescription: b\n---\nbody-b\n",
        }
        context, _, _ = _make_context(tmp_path, skills=skills)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)

        plugin = CodexSkillsPlugin()
        plugin.install(context)

        manifest = json.loads(
            (codex_skills_dir / ".nwave-manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["installed_skills"] == ["nw-alpha", "nw-beta"]


class TestVerify:
    """verify: success path after install."""

    def test_verify_passes_after_successful_install(self, tmp_path, monkeypatch):
        """
        GIVEN: A successful install
        WHEN: verify() runs
        THEN: Returns success
        """
        context, _, _ = _make_context(tmp_path)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)

        plugin = CodexSkillsPlugin()
        plugin.install(context)
        result = plugin.verify(context)

        assert result.success is True


class TestUninstallRemovesOnlyNwaveSkills:
    """uninstall: removes only manifest-listed skills, preserves others."""

    def test_uninstall_preserves_user_created_skills(self, tmp_path, monkeypatch):
        """
        GIVEN: nWave-installed skill (nw-test-skill) AND a user-created skill
               (custom-user-skill) in the same target directory
        WHEN: uninstall() runs
        THEN: nw-test-skill is removed, custom-user-skill is preserved,
              and the manifest is removed.
        """
        context, _, _ = _make_context(tmp_path)
        codex_skills_dir = tmp_path / "home" / ".agents" / "skills"
        codex_config_dir = tmp_path / "home" / ".codex"
        codex_config_dir.mkdir(parents=True)
        _patch_codex_dirs(monkeypatch, codex_skills_dir, codex_config_dir)

        plugin = CodexSkillsPlugin()
        plugin.install(context)

        # Plant a user-created skill the plugin must NOT touch
        user_dir = codex_skills_dir / "custom-user-skill"
        user_dir.mkdir()
        user_md = user_dir / "SKILL.md"
        user_md.write_text(
            "---\nname: custom-user-skill\n---\nbody\n", encoding="utf-8"
        )

        tracked_keys = {
            "nw-test-skill.exists",
            "custom-user-skill.exists",
            "manifest.exists",
        }

        def snapshot() -> dict[str, object]:
            return {
                "nw-test-skill.exists": (
                    codex_skills_dir / "nw-test-skill" / "SKILL.md"
                ).is_file(),
                "custom-user-skill.exists": user_md.is_file(),
                "manifest.exists": (
                    codex_skills_dir / ".nwave-manifest.json"
                ).is_file(),
            }

        before = snapshot()
        assert before == {
            "nw-test-skill.exists": True,
            "custom-user-skill.exists": True,
            "manifest.exists": True,
        }

        result = plugin.uninstall(context)

        after = snapshot()

        assert result.success is True
        assert_state_delta(
            before,
            after,
            universe=tracked_keys,
            expected={
                "nw-test-skill.exists": set_to(False),
                "manifest.exists": set_to(False),
                # custom-user-skill.exists is implicit-unchanged
            },
        )
