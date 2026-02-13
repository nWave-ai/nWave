"""Unit tests for skills verification output formatting.

Tests validate that:
- _skill_group_emoji() maps known roles to their emojis
- _skill_group_emoji() strips '-reviewer' suffix to find base role emoji
- _skill_group_emoji() returns fallback emoji for unknown roles
- verify() logs a summary line followed by indented per-group lines with emojis
- verify() outputs groups in alphabetical order
"""

from unittest.mock import MagicMock

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.skills_plugin import SkillsPlugin, _skill_group_emoji


class TestSkillGroupEmoji:
    """Test emoji lookup for skill group names."""

    @pytest.mark.parametrize(
        "group_name,expected_emoji",
        [
            ("software-crafter", "\U0001f4bb"),
            ("acceptance-designer", "\u2705"),
            ("solution-architect", "\U0001f3d7\ufe0f"),
            ("devop", "\U0001f527"),
        ],
    )
    def test_skill_group_emoji_known_role(self, group_name, expected_emoji):
        """
        GIVEN: A known skill group name
        WHEN: _skill_group_emoji is called
        THEN: Returns the mapped emoji for that role
        """
        assert _skill_group_emoji(group_name) == expected_emoji

    def test_skill_group_emoji_reviewer_uses_base_role(self):
        """
        GIVEN: A reviewer skill group name (e.g. 'software-crafter-reviewer')
        WHEN: _skill_group_emoji is called
        THEN: Returns the emoji for the base role (strips '-reviewer')
        """
        assert _skill_group_emoji("software-crafter-reviewer") == "\U0001f4bb"

    def test_skill_group_emoji_unknown_role_returns_fallback(self):
        """
        GIVEN: An unrecognized skill group name
        WHEN: _skill_group_emoji is called
        THEN: Returns the fallback emoji
        """
        assert _skill_group_emoji("unknown-thing") == "\U0001f4e6"


class TestVerifyLogsMultilineGroups:
    """Test that verify() logs multi-line output with emojis."""

    def _make_context(self, tmp_path):
        """Create an InstallContext with skill group directories containing .md files."""
        claude_dir = tmp_path / ".claude"
        skills_nw = claude_dir / "skills" / "nw"

        # Also create framework_source and project_root so verify()
        # doesn't short-circuit on "no skills configured"
        framework_source = tmp_path / "framework"
        project_root = tmp_path / "project"
        nwave_skills = project_root / "nWave" / "skills"
        nwave_skills.mkdir(parents=True)

        logger = MagicMock()
        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "templates",
            logger=logger,
            project_root=project_root,
            framework_source=framework_source,
        )
        return context, skills_nw, logger

    def _create_skill_groups(self, skills_nw, group_names):
        """Create skill group directories with a .md file in each."""
        for name in group_names:
            group_dir = skills_nw / name
            group_dir.mkdir(parents=True, exist_ok=True)
            (group_dir / "skill.md").write_text(f"# {name} skill")

    def test_verify_logs_multiline_groups(self, tmp_path):
        """
        GIVEN: 3 skill groups installed under skills/nw/
        WHEN: verify() is called
        THEN: Logger receives a summary line and per-group lines with emojis
        """
        context, skills_nw, logger = self._make_context(tmp_path)
        self._create_skill_groups(
            skills_nw, ["software-crafter", "devop", "researcher"]
        )

        plugin = SkillsPlugin()
        result = plugin.verify(context)

        assert result.success is True

        # Collect all info log messages
        info_calls = [str(call.args[0]) for call in logger.info.call_args_list]

        # Summary line must contain file count and group count
        summary_lines = [c for c in info_calls if "Verified" in c and "groups:" in c]
        assert len(summary_lines) == 1
        assert "3 skill files" in summary_lines[0]
        assert "3 groups:" in summary_lines[0]

        # Per-group lines: indented with emoji and group name
        group_lines = [c for c in info_calls if c.startswith("    ")]
        assert len(group_lines) == 3

        # Check each expected group appears with its emoji
        group_text = "\n".join(group_lines)
        assert "\U0001f4bb software-crafter" in group_text
        assert "\U0001f527 devop" in group_text
        assert "\U0001f52c researcher" in group_text

    def test_verify_groups_sorted_alphabetically(self, tmp_path):
        """
        GIVEN: Skill groups installed in non-alphabetical order
        WHEN: verify() is called
        THEN: Per-group log lines appear in alphabetical order
        """
        context, skills_nw, logger = self._make_context(tmp_path)
        # Create in reverse-alphabetical order
        self._create_skill_groups(
            skills_nw, ["software-crafter", "devop", "acceptance-designer"]
        )

        plugin = SkillsPlugin()
        plugin.verify(context)

        info_calls = [str(call.args[0]) for call in logger.info.call_args_list]
        group_lines = [c for c in info_calls if c.startswith("    ")]

        # Extract group names from lines like "    {emoji} {name}"
        group_names = [line.strip().split(" ", 1)[1] for line in group_lines]
        assert group_names == sorted(group_names)
        assert group_names == [
            "acceptance-designer",
            "devop",
            "software-crafter",
        ]
