"""Unit tests for OpenCode skills installer plugin.

Tests validate that:
- install() transforms nWave skills into OpenCode SKILL.md format
- install() prefixes duplicate skill names with their agent group name
- install() preserves file content (frontmatter + body) exactly
- verify() checks that installed SKILL.md files exist with valid frontmatter
- uninstall() only removes skills listed in the manifest, not user-created skills
- install() creates a manifest file tracking installed skill names

CRITICAL: Tests follow hexagonal architecture - mocks only at port boundaries.

State-delta migration summary
------------------------------
CONVERTED (8 tests) — state-delta + implicit-unchanged invariant:
  - test_install_transforms_skill_to_opencode_format: skill dir + manifest created;
    implicit-unchanged catches any unintended sibling dir mutations
  - test_install_prefixes_duplicate_skill_names: two prefixed dirs created, bare
    name absent, frontmatter names rewritten; implicit-unchanged on target universe
  - test_install_preserves_frontmatter: content slot frozen (set_to original);
    manifest slot also declared; implicit-unchanged on file body
  - test_uninstall_removes_only_nwave_skills: nwave dir removed, user dir preserved,
    manifest removed; implicit-unchanged on user-created skill content
  - test_install_creates_manifest: manifest content (installed_skills list) +
    skill dirs presence; implicit-unchanged on unrelated sibling slots
  - test_install_manifest_includes_prefixed_names_for_duplicates: manifest lists
    prefixed names; implicit-unchanged on bare-name absence
  - test_install_strips_user_invocable_field: content slot excludes forbidden key;
    implicit-unchanged catches body and name/description mutations
  - test_install_strips_both_forbidden_fields: both forbidden keys absent; name +
    description slots declared as preserved

KEPT as-is (5 tests) — no state-delta benefit:
  - test_verify_checks_skill_md_exists: single result.success (no state mutation)
  - test_verify_fails_when_skill_md_missing: result properties on error path
  - test_install_preserves_essential_fields_when_no_forbidden_fields: content
    equality already minimal; no extra slots to guard
  - test_install_strips_disable_model_invocation_field: same single-field pattern
    as user_invocable; kept to document the distinct field name
  - (test_uninstall_removes_manifest merged into test_uninstall_removes_only_nwave_skills)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.opencode_skills_plugin import OpenCodeSkillsPlugin


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _skill_filesystem_state(
    target_dir: Path,
    track: frozenset[str] | None = None,
) -> dict[str, object]:
    """Return a flat state dict for the OpenCode skills target directory.

    Tracks existence of immediate subdirectories (skill dirs) and the manifest
    file. Each key is a dotted path: "<dir-name>.exists" or "manifest.exists".

    When ``track`` is provided, every name in the set is always emitted — with
    ``True`` if the dir exists and ``False`` if it does not. This allows the
    uninstall tests to assert ``set_to(False)`` on removed dirs, because the
    key appears in both ``before`` and ``after`` with a concrete Boolean value.

    Without ``track``, only currently-existing dirs are emitted (``True`` only).
    That mode is correct for install tests where we never need to assert absence
    of a dir that was never present before the operation.

    Args:
        target_dir: Path to the OpenCode skills directory (may not yet exist).
        track: Optional explicit set of dir names to always include in state.

    Returns:
        Flat dict mapping slot names to their current values.
    """
    state: dict[str, object] = {
        "manifest.exists": (target_dir / ".nwave-manifest.json").exists(),
    }
    # Emit tracked names with explicit True/False so before/after share the key.
    if track is not None:
        for name in track:
            state[f"{name}.exists"] = (target_dir / name).is_dir()
    elif target_dir.exists():
        for entry in sorted(target_dir.iterdir()):
            if entry.is_dir():
                state[f"{entry.name}.exists"] = True
    return state


def _skill_content_state(target_dir: Path, skill_name: str) -> dict[str, object]:
    """Return a flat state dict for an installed skill's SKILL.md content.

    Slots: "content.has_user_invocable", "content.has_disable_model_invocation",
    "content.name_line", "content.description_line", "content.full".

    Args:
        target_dir: Path to the OpenCode skills directory.
        skill_name: Resolved skill name (directory name under target_dir).

    Returns:
        Flat dict with content property slots.
    """
    skill_md = target_dir / skill_name / "SKILL.md"
    if not skill_md.exists():
        return {
            "content.exists": False,
            "content.has_user_invocable": False,
            "content.has_disable_model_invocation": False,
            "content.name_line": None,
            "content.description_line": None,
            "content.full": None,
        }
    text = skill_md.read_text(encoding="utf-8")
    name_line = next(
        (line for line in text.splitlines() if line.startswith("name:")), None
    )
    desc_line = next(
        (line for line in text.splitlines() if line.startswith("description:")), None
    )
    return {
        "content.exists": True,
        "content.has_user_invocable": "user-invocable" in text,
        "content.has_disable_model_invocation": "disable-model-invocation" in text,
        "content.name_line": name_line,
        "content.description_line": desc_line,
        "content.full": text,
    }


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_context(tmp_path):
    """Create an InstallContext with a minimal skill source layout.

    Returns:
        Tuple of (context, skills_source, opencode_skills_target)
    """
    project_root = tmp_path / "project"
    framework_source = tmp_path / "framework"

    skills_source = project_root / "nWave" / "skills"
    skills_source.mkdir(parents=True)

    # Create minimal catalog to satisfy fail-closed load_public_agents.
    # Empty agents section -> public_agents is empty -> all skills treated as public.
    (project_root / "nWave" / "framework-catalog.yaml").write_text("agents: {}\n")

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    logger = MagicMock()

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=tmp_path / "templates",
        logger=logger,
        project_root=project_root,
        framework_source=framework_source,
    )

    opencode_skills_target = tmp_path / "home" / ".config" / "opencode" / "skills"

    return context, skills_source, opencode_skills_target


def _create_skill(skills_source, agent_name, skill_name, content=None):
    """Create a skill .md file in the source layout.

    Args:
        skills_source: Path to nWave/skills/ directory
        agent_name: Agent group name (e.g. 'software-crafter')
        skill_name: Skill name without extension (e.g. 'tdd-methodology')
        content: Optional content; if None, generates default frontmatter + body
    """
    agent_dir = skills_source / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    if content is None:
        content = (
            f"---\n"
            f"name: {skill_name}\n"
            f"description: {skill_name} description for {agent_name}\n"
            f"---\n"
            f"\n"
            f"# {skill_name}\n"
            f"\n"
            f"Content for {skill_name} in {agent_name}.\n"
        )

    (agent_dir / f"{skill_name}.md").write_text(content)


# ---------------------------------------------------------------------------
# Tests: install() — format transformation
# ---------------------------------------------------------------------------


class TestInstallTransformsSkillToOpenCodeFormat:
    """Test that install() creates {skill-name}/SKILL.md structure."""

    def test_install_transforms_skill_to_opencode_format(self, tmp_path, monkeypatch):
        """
        GIVEN: A source skill at software-crafter/tdd-methodology.md
        WHEN: install() is called
        THEN: The skill appears as tdd-methodology/SKILL.md in the target;
              no other skill dirs are created as a side-effect.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        _create_skill(skills_source, "software-crafter", "tdd-methodology")

        before = _skill_filesystem_state(target)

        plugin = OpenCodeSkillsPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _skill_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "tdd-methodology.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )


class TestInstallPrefixesDuplicateSkillNames:
    """Test that install() prefixes colliding skill names with agent group."""

    def test_install_prefixes_duplicate_skill_names(self, tmp_path, monkeypatch):
        """
        GIVEN: Two skills with the same name in different agent groups
               (software-crafter/critique-dimensions.md and
                agent-builder/critique-dimensions.md)
        WHEN: install() is called
        THEN: Both appear with agent-prefixed names:
              software-crafter-critique-dimensions/SKILL.md
              agent-builder-critique-dimensions/SKILL.md;
              the bare name is never created;
              frontmatter name: fields match the prefixed directory names.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        _create_skill(skills_source, "software-crafter", "critique-dimensions")
        _create_skill(skills_source, "agent-builder", "critique-dimensions")

        before = _skill_filesystem_state(target)

        plugin = OpenCodeSkillsPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _skill_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "software-crafter-critique-dimensions.exists": set_to(True),
                "agent-builder-critique-dimensions.exists": set_to(True),
                "manifest.exists": set_to(True),
                # bare name must NOT appear: implicit-unchanged enforces this since
                # "critique-dimensions.exists" is NOT in expected and starts as absent
            },
        )

        # Frontmatter name: must match the prefixed directory name
        sc_content = (
            target / "software-crafter-critique-dimensions" / "SKILL.md"
        ).read_text()
        assert "name: software-crafter-critique-dimensions" in sc_content
        ab_content = (
            target / "agent-builder-critique-dimensions" / "SKILL.md"
        ).read_text()
        assert "name: agent-builder-critique-dimensions" in ab_content


# ---------------------------------------------------------------------------
# Tests: install() — content preservation
# ---------------------------------------------------------------------------


class TestInstallPreservesFrontmatter:
    """Test that install() copies file content without modification."""

    def test_install_preserves_frontmatter(self, tmp_path, monkeypatch):
        """
        GIVEN: A source skill file with frontmatter and body content
        WHEN: install() transforms it to SKILL.md
        THEN: The SKILL.md content is byte-for-byte identical to the source;
              no other content slots are mutated.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        original_content = (
            "---\n"
            "name: tdd-methodology\n"
            "description: Deep knowledge for Outside-In TDD\n"
            "---\n"
            "\n"
            "# Outside-In TDD Methodology\n"
            "\n"
            "## Double-Loop TDD Architecture\n"
            "\n"
            "Outer loop: ATDD/E2E Tests.\n"
        )

        _create_skill(
            skills_source, "software-crafter", "tdd-methodology", original_content
        )

        before = _skill_content_state(target, "tdd-methodology")

        plugin = OpenCodeSkillsPlugin()
        plugin.install(context)

        after = _skill_content_state(target, "tdd-methodology")
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.full": set_to(original_content),
                "content.has_user_invocable": set_to(False),
                "content.has_disable_model_invocation": set_to(False),
                "content.name_line": set_to("name: tdd-methodology"),
                "content.description_line": set_to(
                    "description: Deep knowledge for Outside-In TDD"
                ),
            },
        )


# ---------------------------------------------------------------------------
# Tests: verify()
# ---------------------------------------------------------------------------


class TestVerifyChecksSkillMdExists:
    """Test that verify() validates SKILL.md presence in installed skills."""

    def test_verify_checks_skill_md_exists(self, tmp_path, monkeypatch):
        """
        GIVEN: Skills installed with valid SKILL.md files and a manifest
        WHEN: verify() is called
        THEN: Verification passes
        """
        context, _skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        # Create installed skill structure directly
        skill_dir = target / "tdd-methodology"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: tdd-methodology\ndescription: test\n---\n\n# Test\n"
        )

        # Create manifest
        manifest = {"installed_skills": ["tdd-methodology"], "version": "1.0"}
        (target / ".nwave-manifest.json").write_text(json.dumps(manifest))

        plugin = OpenCodeSkillsPlugin()
        result = plugin.verify(context)

        assert result.success is True

    def test_verify_fails_when_skill_md_missing(self, tmp_path, monkeypatch):
        """
        GIVEN: A skill directory exists but SKILL.md is missing
        WHEN: verify() is called
        THEN: Verification fails with an error
        """
        context, _skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        # Create directory without SKILL.md
        skill_dir = target / "tdd-methodology"
        skill_dir.mkdir(parents=True)

        # Create manifest referencing this skill
        manifest = {"installed_skills": ["tdd-methodology"], "version": "1.0"}
        (target / ".nwave-manifest.json").write_text(json.dumps(manifest))

        plugin = OpenCodeSkillsPlugin()
        result = plugin.verify(context)

        assert result.success is False
        assert any("tdd-methodology" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Tests: uninstall()
# ---------------------------------------------------------------------------


class TestUninstallRemovesOnlyNwaveSkills:
    """Test that uninstall() only removes manifest-tracked skills."""

    def test_uninstall_removes_only_nwave_skills(self, tmp_path, monkeypatch):
        """
        GIVEN: An OpenCode skills directory with both nWave-installed and
               user-created skills, plus a manifest
        WHEN: uninstall() is called
        THEN: Only nWave-installed skills (listed in manifest) are removed;
              user-created skills remain untouched;
              the manifest itself is also removed.
        """
        context, _skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        # Create nWave-installed skill
        nwave_skill = target / "tdd-methodology"
        nwave_skill.mkdir(parents=True)
        (nwave_skill / "SKILL.md").write_text("---\nname: tdd-methodology\n---\n")

        # Create user-owned skill (NOT in manifest)
        user_skill = target / "my-custom-skill"
        user_skill.mkdir(parents=True)
        (user_skill / "SKILL.md").write_text("---\nname: my-custom-skill\n---\n")

        # Manifest only tracks nWave skills
        manifest = {"installed_skills": ["tdd-methodology"], "version": "1.0"}
        (target / ".nwave-manifest.json").write_text(json.dumps(manifest))

        tracked = frozenset({"tdd-methodology", "my-custom-skill"})
        before = _skill_filesystem_state(target, track=tracked)

        plugin = OpenCodeSkillsPlugin()
        result = plugin.uninstall(context)

        assert result.success is True

        after = _skill_filesystem_state(target, track=tracked)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                # nWave skill removed: True -> False
                "tdd-methodology.exists": set_to(False),
                # manifest removed: True -> False
                "manifest.exists": set_to(False),
                # user skill MUST remain: implicit-unchanged enforces this;
                # "my-custom-skill.exists" True->True, NOT in expected
            },
        )


# ---------------------------------------------------------------------------
# Tests: install() — manifest creation
# ---------------------------------------------------------------------------


class TestInstallCreatesManifest:
    """Test that install() creates a manifest tracking installed skills."""

    def test_install_creates_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: Multiple source skills across agent groups
        WHEN: install() is called
        THEN: A .nwave-manifest.json is created listing all installed skill names;
              no other filesystem mutations occur outside the declared universe.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        _create_skill(skills_source, "software-crafter", "tdd-methodology")
        _create_skill(skills_source, "software-crafter", "quality-framework")
        _create_skill(skills_source, "acceptance-designer", "bdd-methodology")

        before = _skill_filesystem_state(target)

        plugin = OpenCodeSkillsPlugin()
        plugin.install(context)

        after = _skill_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "tdd-methodology.exists": set_to(True),
                "quality-framework.exists": set_to(True),
                "bdd-methodology.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )

        manifest = json.loads((target / ".nwave-manifest.json").read_text())
        assert sorted(manifest["installed_skills"]) == sorted(
            ["tdd-methodology", "quality-framework", "bdd-methodology"]
        )

    def test_install_manifest_includes_prefixed_names_for_duplicates(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN: Skills with duplicate names across agent groups
        WHEN: install() is called
        THEN: The manifest lists the prefixed names, not the bare names;
              the bare-named directory is not created in the target.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        _create_skill(skills_source, "software-crafter", "critique-dimensions")
        _create_skill(skills_source, "agent-builder", "critique-dimensions")
        _create_skill(skills_source, "software-crafter", "tdd-methodology")

        before = _skill_filesystem_state(target)

        plugin = OpenCodeSkillsPlugin()
        plugin.install(context)

        after = _skill_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "software-crafter-critique-dimensions.exists": set_to(True),
                "agent-builder-critique-dimensions.exists": set_to(True),
                "tdd-methodology.exists": set_to(True),
                "manifest.exists": set_to(True),
                # "critique-dimensions.exists" NOT in expected ->
                # implicit-unchanged would catch it if the bare dir were created
            },
        )

        manifest = json.loads((target / ".nwave-manifest.json").read_text())
        installed = sorted(manifest["installed_skills"])
        assert installed == sorted(
            [
                "agent-builder-critique-dimensions",
                "software-crafter-critique-dimensions",
                "tdd-methodology",
            ]
        )


# ---------------------------------------------------------------------------
# Tests: install() — forbidden field stripping (ANOMALY-2)
# ---------------------------------------------------------------------------


class TestInstallStripsForbiddenFields:
    """ANOMALY-2: Skills with Claude Code-only frontmatter fields have them stripped."""

    def test_install_strips_user_invocable_field(self, tmp_path, monkeypatch):
        """
        GIVEN: A skill with 'user-invocable: false' in frontmatter
        WHEN: install() is called
        THEN: The installed SKILL.md does NOT contain 'user-invocable';
              name and description are preserved unchanged.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        content = (
            "---\n"
            "name: tdd-methodology\n"
            "description: Deep knowledge for Outside-In TDD\n"
            "user-invocable: false\n"
            "---\n"
            "\n"
            "# Outside-In TDD Methodology\n"
        )
        _create_skill(skills_source, "software-crafter", "tdd-methodology", content)

        before = _skill_content_state(target, "tdd-methodology")

        plugin = OpenCodeSkillsPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _skill_content_state(target, "tdd-methodology")
        universe = set(before.keys()) | set(after.keys())

        def user_invocable_stripped(old: object, new: object) -> bool:
            return isinstance(new, str) and "user-invocable" not in new

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.full": user_invocable_stripped,
                "content.has_user_invocable": set_to(False),
                "content.has_disable_model_invocation": set_to(False),
                "content.name_line": set_to("name: tdd-methodology"),
                "content.description_line": set_to(
                    "description: Deep knowledge for Outside-In TDD"
                ),
            },
        )

    def test_install_strips_disable_model_invocation_field(self, tmp_path, monkeypatch):
        """
        GIVEN: A skill with 'disable-model-invocation: true' in frontmatter
        WHEN: install() is called
        THEN: The installed SKILL.md does NOT contain 'disable-model-invocation'
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        content = (
            "---\n"
            "name: quality-framework\n"
            "description: Quality gates\n"
            "disable-model-invocation: true\n"
            "---\n"
            "\n"
            "# Quality Framework\n"
        )
        _create_skill(skills_source, "software-crafter", "quality-framework", content)

        plugin = OpenCodeSkillsPlugin()
        result = plugin.install(context)

        assert result.success is True
        installed_content = (target / "quality-framework" / "SKILL.md").read_text()
        assert "disable-model-invocation" not in installed_content
        assert "name: quality-framework" in installed_content

    def test_install_strips_both_forbidden_fields(self, tmp_path, monkeypatch):
        """
        GIVEN: A skill with BOTH forbidden fields in frontmatter
        WHEN: install() is called
        THEN: Both fields are stripped; name and description preserved;
              implicit-unchanged catches any unintended body mutation.
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        content = (
            "---\n"
            "name: fp-principles\n"
            "description: Core FP thinking patterns\n"
            "user-invocable: false\n"
            "disable-model-invocation: true\n"
            "---\n"
            "\n"
            "# FP Principles\n"
        )
        _create_skill(skills_source, "software-crafter", "fp-principles", content)

        before = _skill_content_state(target, "fp-principles")

        plugin = OpenCodeSkillsPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _skill_content_state(target, "fp-principles")
        universe = set(before.keys()) | set(after.keys())

        def both_forbidden_stripped(old: object, new: object) -> bool:
            return (
                isinstance(new, str)
                and "user-invocable" not in new
                and "disable-model-invocation" not in new
            )

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.full": both_forbidden_stripped,
                "content.has_user_invocable": set_to(False),
                "content.has_disable_model_invocation": set_to(False),
                "content.name_line": set_to("name: fp-principles"),
                "content.description_line": set_to(
                    "description: Core FP thinking patterns"
                ),
            },
        )

    def test_install_preserves_essential_fields_when_no_forbidden_fields(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN: A skill with NO forbidden fields (only name and description)
        WHEN: install() is called
        THEN: Content is preserved unchanged
        """
        context, skills_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_skills_plugin._opencode_skills_dir",
            lambda: target,
        )

        content = (
            "---\n"
            "name: clean-skill\n"
            "description: A skill without forbidden fields\n"
            "---\n"
            "\n"
            "# Clean Skill\n"
        )
        _create_skill(skills_source, "software-crafter", "clean-skill", content)

        plugin = OpenCodeSkillsPlugin()
        plugin.install(context)

        installed_content = (target / "clean-skill" / "SKILL.md").read_text()
        assert installed_content == content
