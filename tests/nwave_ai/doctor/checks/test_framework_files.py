"""Acceptance tests for FrameworkFilesCheck.

Tests enter through the check's run() driving port.

Pass path: agents/ and skills/ exist and contain at least 1 .md file each.
Fail path: agents/ or skills/ absent or empty.

Note: commands/ is intentionally NOT required. Since v2.8.0 the framework
delivers commands as skills under skills/nw-*/SKILL.md; commands_plugin.py
removes any legacy commands/nw/ directory on every install. Asserting
its presence would yield a false-positive on every clean install.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from nwave_ai.doctor.checks.framework_files import FrameworkFilesCheck
from nwave_ai.doctor.context import DoctorContext


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def context(tmp_path: Path) -> DoctorContext:
    return DoctorContext(home_dir=tmp_path)


def _populate_required_dirs(context: DoctorContext) -> None:
    """Create agents/ and skills/ each with one stub .md file."""
    for subdir in ("agents", "skills"):
        d = context.claude_dir / subdir
        d.mkdir(parents=True)
        (d / "example.md").write_text("# stub\n")


def test_passes_when_agents_and_skills_populated_no_commands_dir(
    context: DoctorContext,
) -> None:
    """Pass on a fresh v3.12.2+ install: agents/ + skills/ populated, no commands/ dir.

    Regression guard for Bug #4 of v3.12.1 install regression: doctor previously
    required commands/ even though commands_plugin.py since v2.8.0 deletes that
    legacy directory.
    """
    _populate_required_dirs(context)
    # Deliberately NO commands/ directory — this is the post-v2.8.0 install layout.
    assert not (context.claude_dir / "commands").exists()

    check = FrameworkFilesCheck()
    result = check.run(context)

    assert result.passed is True, (
        f"Expected PASS without commands/, got: {result.message}"
    )
    assert "missing" not in result.message
    # Message must not advertise a non-existent commands/ count.
    assert "commands" not in result.message


def test_passes_when_all_dirs_populated(context: DoctorContext) -> None:
    """Pass when agents/ + skills/ are populated (commands/ presence is irrelevant)."""
    _populate_required_dirs(context)
    # Even if a stray commands/ exists, the check should still pass.
    commands_dir = context.claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "legacy.md").write_text("# legacy\n")

    check = FrameworkFilesCheck()
    result = check.run(context)

    assert result.passed is True
    assert "agents" in result.message
    assert "skills" in result.message


def test_fails_when_agents_missing(context: DoctorContext) -> None:
    """Fail when agents/ directory is absent."""
    skills = context.claude_dir / "skills"
    skills.mkdir(parents=True)
    (skills / "file.md").write_text("# stub\n")

    check = FrameworkFilesCheck()
    result = check.run(context)

    assert result.passed is False
    assert "agents" in result.message
    assert result.remediation is not None


def test_fails_when_skills_missing(context: DoctorContext) -> None:
    """Fail when skills/ directory is absent."""
    agents = context.claude_dir / "agents"
    agents.mkdir(parents=True)
    (agents / "file.md").write_text("# stub\n")

    check = FrameworkFilesCheck()
    result = check.run(context)

    assert result.passed is False
    assert "skills" in result.message
    assert result.remediation is not None


def test_fails_when_agents_dir_empty(context: DoctorContext) -> None:
    """Fail when agents/ exists but contains no .md files."""
    (context.claude_dir / "agents").mkdir(parents=True)
    skills = context.claude_dir / "skills"
    skills.mkdir(parents=True)
    (skills / "file.md").write_text("# stub\n")

    check = FrameworkFilesCheck()
    result = check.run(context)

    assert result.passed is False
    assert "agents" in result.message


def test_passes_with_realistic_install_layout(context: DoctorContext) -> None:
    """Pass when files are nested in subdirectories (real install layout).

    Real install has agents/nw/*.md and skills/*/SKILL.md.
    Recursive discovery handles both layouts.
    """
    # agents/nw/nw-foo.md (nested)
    agents_nw = context.claude_dir / "agents" / "nw"
    agents_nw.mkdir(parents=True)
    (agents_nw / "nw-foo.md").write_text("# agent\n")

    # skills/nw-bar/SKILL.md (directory per skill)
    skill_dir = context.claude_dir / "skills" / "nw-bar"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill\n")

    check = FrameworkFilesCheck()
    result = check.run(context)
    assert result.passed is True, (
        f"Expected PASS with real layout, got: {result.message}"
    )


def test_fails_when_skills_dir_contains_only_backup_files(
    context: DoctorContext,
) -> None:
    """Fail when skills/ contains only *.md.bak files (no real .md files)."""
    (context.claude_dir / "agents").mkdir(parents=True)
    (context.claude_dir / "agents" / "nw-foo.md").write_text("# agent\n")

    (context.claude_dir / "skills").mkdir(parents=True)
    (context.claude_dir / "skills" / "nw-bar.md.bak").write_text("# backup\n")

    check = FrameworkFilesCheck()
    result = check.run(context)
    assert result.passed is False, (
        f"Expected FAIL when skills/ has only .md.bak, got: {result.message}"
    )
    assert "skills" in result.message
