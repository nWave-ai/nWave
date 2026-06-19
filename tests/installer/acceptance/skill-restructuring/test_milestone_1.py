"""
Milestone 1 Acceptance Tests: Collision-Free Skills.

All scenarios except the first are marked @skip. Enable one at a time
as implementation progresses.

Driving ports: SkillsPlugin.install(), SkillsPlugin.verify()
"""

from pytest_bdd import scenario


@scenario(
    "milestone-1-collision-free.feature",
    "All non-colliding skills exist in nw-prefixed directory format",
)
def test_source_structure_nw_prefixed():
    """Source tree has nw-prefixed directories with SKILL.md."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Skill content is preserved after restructuring",
)
def test_content_preserved():
    """File content identical after restructuring."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Skills plugin installs all collision-free skills",
)
def test_install_collision_free():
    """Install 94 non-colliding skills."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Installation reports correct file count",
)
def test_install_reports_count():
    """Installation message includes correct count."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Old namespace directory removed during upgrade installation",
)
def test_upgrade_removes_old_namespace():
    """Upgrade cleans old nw/ directory."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Upgrade replaces all old skills with new layout",
)
def test_upgrade_replaces_layout():
    """Upgrade from old to new layout."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Verification passes when all skills are installed correctly",
)
def test_verify_success():
    """Verification reports success."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Verification detects missing skill directories",
)
def test_verify_detects_missing():
    """Verification catches missing skills."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Agent Skill Loading sections reference new nw-prefixed Read paths",
)
def test_agent_skill_loading_paths():
    """All agent Skill Loading paths use nw-prefixed SKILL.md format."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Installation fails gracefully when source directory is missing",
)
def test_error_no_source():
    """Graceful handling of missing source."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Installation handles read-only target directory",
)
def test_error_readonly_target():
    """Permission error handled gracefully."""
    pass


@scenario(
    "milestone-1-collision-free.feature",
    "Verification handles missing target directory",
)
def test_error_no_target():
    """Verification handles missing target."""
    pass


# =============================================================================
# RUNTIME GUARD: Installed skill files are actually readable on disk
# (Category A -> runtime layer)
#
# The BDD scenarios above call SkillsPlugin.install() and assert result.success.
# They do NOT verify the files physically landed in the target directory with
# correct content. This test answers the orthogonal question:
#   "Are the installed SKILL.md files readable from the target path?"
#
# Deletion test: if copy_skills_to_target() had a silent bug that reported
# success but wrote nothing, all BDD assertions above would still PASS, but
# this test would FAIL -- catching the regression before users discover their
# agents cannot load skills.
# =============================================================================


def test_skills_install_writes_readable_files_to_target(
    skills_plugin,
    install_context,
    populate_troubleshooter_skills,
):
    """
    GIVEN a source tree with 3 nw-prefixed troubleshooter skill directories
    WHEN SkillsPlugin.install() is called through the driving port
    THEN each skill SKILL.md exists in the target directory
    AND installed content matches source content byte-for-byte

    Runtime counterpart to the BDD Skills plugin installs all collision-free
    skills scenario. That scenario checks result.success; this test verifies
    the actual filesystem outcome -- the files users agents will read.
    """
    skills_source = install_context.framework_source / "skills"
    skills_target = install_context.claude_dir / "skills"

    result = skills_plugin.install(install_context)

    assert result.success, f"Install failed unexpectedly: {result.message}"

    for skill_name in populate_troubleshooter_skills:
        source_skill_md = skills_source / skill_name / "SKILL.md"
        target_skill_md = skills_target / skill_name / "SKILL.md"

        assert target_skill_md.exists(), (
            f"Installed SKILL.md missing at {target_skill_md}.\n"
            f"SkillsPlugin.install() reported success but did not write the file."
        )
        assert target_skill_md.stat().st_size > 0, (
            f"Installed SKILL.md is empty at {target_skill_md}."
        )

        source_content = source_skill_md.read_text(encoding="utf-8")
        installed_content = target_skill_md.read_text(encoding="utf-8")
        assert source_content == installed_content, (
            f"Content mismatch for {skill_name}/SKILL.md.\n"
            f"Source and installed content diverged -- copy_skills_to_target "
            f"may have written the wrong file."
        )
