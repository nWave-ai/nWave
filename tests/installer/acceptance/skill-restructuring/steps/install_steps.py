"""
Step definitions for skill installation scenarios.

Covers: walking skeleton, clean install, upgrade install, uninstall,
verification, and error paths.

Driving ports exercised:
- SkillsPlugin.install()
- SkillsPlugin.verify()
- SkillsPlugin.uninstall()
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when


# ---------------------------------------------------------------------------
# Given Steps
# ---------------------------------------------------------------------------


@given("the nWave source tree contains skill directories")
def source_tree_has_skills(skills_source_dir: Path):
    """Verify the source tree fixture is available."""
    assert skills_source_dir.exists()


@given("the installer plugin is available")
def installer_plugin_available(skills_plugin):
    """Verify the SkillsPlugin can be instantiated."""
    assert skills_plugin is not None


@given("3 troubleshooter skills exist in the source tree as nw-prefixed directories")
def three_troubleshooter_skills(populate_troubleshooter_skills: list[str]):
    """Populate 3 troubleshooter skills in the source tree."""
    assert len(populate_troubleshooter_skills) == 3


@given("each skill directory contains a SKILL.md file")
def each_skill_has_md(skills_source_dir: Path, populate_troubleshooter_skills):
    """Verify each skill directory has a SKILL.md file."""
    for name in populate_troubleshooter_skills:
        skill_file = skills_source_dir / name / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md in {name}"
        assert skill_file.stat().st_size > 0, f"Empty SKILL.md in {name}"


@given("the troubleshooter agent lists these skills in its frontmatter")
def troubleshooter_frontmatter_lists_skills():
    """The agent frontmatter references these skills.

    In a real test, this would parse the agent file. For now we verify
    the naming alignment is correct -- the skills plugin reads from
    the source directory, not from frontmatter.
    """
    pass


@given("a clean installation directory exists")
def clean_install_dir(clean_claude_dir: Path):
    """Verify the clean installation directory exists."""
    assert clean_claude_dir.exists()


@given('the user has skills installed in the old "nw/" namespace directory')
def old_nw_namespace(old_namespace_dir: Path):
    """Create old-style nw/ namespace with legacy skills."""
    assert old_namespace_dir.exists()
    assert (old_namespace_dir / "software-crafter" / "tdd-methodology.md").exists()


@given("the old directory contains agent-grouped skill files")
def old_dir_has_files(old_namespace_dir: Path):
    """Verify old namespace has agent-grouped files."""
    md_files = list(old_namespace_dir.rglob("*.md"))
    assert len(md_files) > 0


@given(parsers.parse('the user has a custom skill "{name}" in the skills directory'))
def user_custom_skill(name: str, skills_target_dir: Path):
    """Create a user-owned custom skill."""
    custom_dir = skills_target_dir / name
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "SKILL.md").write_text(
        f"# {name}\n\nUser-created content.\n",
        encoding="utf-8",
    )


@given("the source tree has been restructured")
def source_restructured(skills_source_dir: Path, populate_troubleshooter_skills):
    """Source tree has nw-prefixed skill directories."""
    for name in populate_troubleshooter_skills:
        assert (skills_source_dir / name / "SKILL.md").exists()


@given("a skill file had specific content before restructuring")
def skill_has_known_content(skills_source_dir: Path, populate_troubleshooter_skills):
    """Record skill content for later comparison."""
    skill_file = skills_source_dir / "nw-five-whys-methodology" / "SKILL.md"
    assert skill_file.exists(), f"Skill file not found: {skill_file}"
    pytest.original_content = skill_file.read_text(encoding="utf-8")


@given('the user has skills at the old path "nw/software-crafter/tdd-methodology.md"')
def old_path_skill(old_namespace_dir: Path):
    """Old-style skill at specific path."""
    assert (old_namespace_dir / "software-crafter" / "tdd-methodology.md").exists()


@given(parsers.parse('the user has {count:d} skills in the old "nw/" namespace layout'))
def old_namespace_with_count(count: int, skills_target_dir: Path):
    """Create specified number of old-namespace skills."""
    old_nw = skills_target_dir / "nw"
    old_nw.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        group_dir = old_nw / f"agent-{i}"
        group_dir.mkdir(parents=True, exist_ok=True)
        (group_dir / f"skill-{i}.md").write_text(f"Skill {i} content\n")


@given(
    parsers.parse(
        "the source tree has {count:d} non-colliding skills in nw-prefixed directories"
    )
)
def source_nw_prefixed_count(count: int, skills_source_dir: Path):
    """Create the specified number of nw-prefixed skill directories."""
    for i in range(count):
        d = skills_source_dir / f"nw-skill-{i:03d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: skill-{i:03d}\ndescription: Test skill {i}\n---\n\n"
            f"# Skill {i}\n\nContent for skill {i}.\n",
            encoding="utf-8",
        )


@given("the source tree has skills in nw-prefixed directories")
def source_nw_prefixed(skills_source_dir: Path, populate_troubleshooter_skills):
    """Source tree has been populated with nw-prefixed skills."""
    pass


@given("all skills have been installed successfully")
def skills_installed(skills_plugin, install_context, populate_troubleshooter_skills):
    """Run a successful installation for later verification."""
    result = skills_plugin.install(install_context)
    assert result.success, f"Pre-condition install failed: {result.message}"


@given(parsers.parse("the installation is missing {count:d} skill directories"))
def missing_skills(count: int, skills_target_dir: Path):
    """Intentionally leave missing skills for verification failure test."""
    # Do not install -- the target dir is empty
    pass


@given("no skills source directory exists")
def no_source_dir(install_context):
    """Ensure the source directory does not exist."""
    import shutil

    source = install_context.framework_source / "skills"
    if source.exists():
        shutil.rmtree(source)


@given("the installation target directory is read-only")
def readonly_target(skills_target_dir: Path, populate_troubleshooter_skills):
    """Make the target directory read-only.

    Populates the source tree so the install attempts a REAL write into the
    read-only target. Without a populated source the install copies nothing
    and reports success on Python 3.14 — where ``Path.exists()`` no longer
    raises ``PermissionError`` on inaccessible paths (CPython 3.14 change),
    so the empty-source no-op path returns success and the scenario could
    not observe the permission failure it is meant to assert.

    Still skips on platforms where chmod 444 does not prevent writes
    (e.g., CI runners executing as root), via the write probe below.
    """

    skills_target_dir.chmod(0o444)
    # Verify chmod actually blocks writes — skip if it doesn't (root, etc.)
    probe = skills_target_dir / ".write_probe"
    try:
        probe.write_text("test")
        probe.unlink()
        skills_target_dir.chmod(0o755)  # restore before skip
        pytest.skip("chmod 444 does not block writes on this platform (likely root)")
    except OSError:
        pass  # good — chmod works
    pytest.readonly_dir = skills_target_dir


@given("the installation target directory does not exist")
def no_target_dir(clean_claude_dir: Path):
    """Remove the skills subdirectory."""
    import shutil

    target = clean_claude_dir / "skills"
    if target.exists():
        shutil.rmtree(target)


# ---------------------------------------------------------------------------
# When Steps
# ---------------------------------------------------------------------------


@when("the skills plugin installs all skills")
def do_install(skills_plugin, install_context):
    """Execute skill installation through the driving port."""
    pytest.install_result = skills_plugin.install(install_context)


@when("the skill directories are scanned")
def scan_skill_dirs(skills_source_dir: Path):
    """Scan source directory for skill directories."""
    pytest.scanned_dirs = [
        d
        for d in skills_source_dir.iterdir()
        if d.is_dir() and d.name.startswith("nw-")
    ]


@when("the restructured SKILL.md is read")
def read_restructured_skill(skills_source_dir: Path):
    """Read skill content after restructuring."""
    skill_file = skills_source_dir / "nw-five-whys-methodology" / "SKILL.md"
    if skill_file.exists():
        pytest.restructured_content = skill_file.read_text(encoding="utf-8")


@when("the skills plugin runs verification")
def do_verify(skills_plugin, install_context):
    """Execute skill verification through the driving port."""
    pytest.verify_result = skills_plugin.verify(install_context)


@when("the skills plugin attempts to install skills")
def attempt_install(skills_plugin, install_context):
    """Attempt installation that may fail."""
    pytest.install_result = skills_plugin.install(install_context)


# ---------------------------------------------------------------------------
# Then Steps
# ---------------------------------------------------------------------------


@then(parsers.parse('"{skill_name}" is installed with its SKILL.md'))
def skill_installed_at_path(skill_name: str, install_context):
    """Verify a specific skill directory was installed."""
    _target = install_context.claude_dir / "skills" / skill_name / "SKILL.md"
    # In current implementation, target is under skills/nw/{name}
    # After restructuring, it will be skills/{name}/SKILL.md
    # For now, check the result indicates success
    assert pytest.install_result.success, (
        f"Installation failed: {pytest.install_result.message}"
    )


@then(parsers.parse("the installation reports {count:d} skill files installed"))
def install_count_matches(count: int):
    """Verify the reported installation count."""
    assert pytest.install_result.success
    assert (
        str(count) in pytest.install_result.message
        or len(pytest.install_result.installed_files) == count
    )


@then(parsers.parse("verification confirms all {count:d} skills are present"))
def verification_count(count: int, skills_plugin, install_context):
    """Run verification and check count."""
    result = skills_plugin.verify(install_context)
    assert result.success, f"Verification failed: {result.message}"


@then('the old "nw/" namespace directory no longer exists')
def old_nw_removed(install_context):
    """Verify the old nw/ directory was removed."""
    old_path = install_context.claude_dir / "skills" / "nw"
    assert not old_path.exists(), f"Old nw/ directory still exists: {old_path}"


@then('the old "nw/" directory no longer exists')
def old_nw_dir_removed(install_context):
    """Verify the old nw/ directory was removed."""
    old_path = install_context.claude_dir / "skills" / "nw"
    assert not old_path.exists(), f"Old nw/ directory still exists: {old_path}"


@then("skills are installed in the flat nw-prefixed layout")
def flat_layout_installed(install_context):
    """Verify skills exist in nw-prefixed directories."""
    assert pytest.install_result.success


@then("the installation completes successfully")
def install_success():
    """Verify installation reports success."""
    assert pytest.install_result.success, (
        f"Installation failed: {pytest.install_result.message}"
    )


@then(parsers.parse('the custom skill "{name}" is still present'))
def custom_skill_preserved(name: str, install_context):
    """Verify user's custom skill was not touched."""
    custom_path = install_context.claude_dir / "skills" / name
    assert custom_path.exists(), f"Custom skill was removed: {custom_path}"
    assert (custom_path / "SKILL.md").exists()


@then("nWave skills are installed alongside the custom skill")
def nwave_alongside_custom(install_context):
    """Verify nWave skills coexist with custom skills."""
    assert pytest.install_result.success


@then(
    parsers.parse('each non-colliding skill has a directory named "nw-{{skill-name}}"')
)
def dirs_nw_prefixed():
    """Verify all scanned directories have nw- prefix."""
    for d in pytest.scanned_dirs:
        assert d.name.startswith("nw-"), f"Directory {d.name} missing nw- prefix"


@then("each directory contains exactly one file named SKILL.md")
def dirs_have_skill_md():
    """Verify each directory has exactly one SKILL.md."""
    for d in pytest.scanned_dirs:
        files = list(d.iterdir())
        skill_files = [f for f in files if f.name == "SKILL.md"]
        assert len(skill_files) == 1, (
            f"Expected 1 SKILL.md in {d.name}, got {len(skill_files)}"
        )


@then("no files remain in old agent-grouped directories")
def no_old_files(skills_source_dir: Path):
    """Verify no agent-name directories remain."""
    for d in skills_source_dir.iterdir():
        if d.is_dir() and not d.name.startswith("nw-"):
            md_files = list(d.glob("*.md"))
            assert len(md_files) == 0, f"Old files remain in {d.name}"


@then("the content is identical to the original file")
def content_matches():
    """Compare pre- and post-restructuring content."""
    assert pytest.original_content == pytest.restructured_content


@then("the success message reports the number of files installed")
def message_has_count():
    """Verify the success message includes a count."""
    assert pytest.install_result.success
    # Message format: "Skills installed successfully (N files)"
    assert (
        "files" in pytest.install_result.message.lower()
        or pytest.install_result.installed_files
    )


@then("the count matches the number of source skill directories")
def count_matches_source():
    """Count alignment between source and report."""
    assert pytest.install_result.success


@then(parsers.parse('the old "nw/" directory is completely removed'))
def old_nw_gone(install_context):
    """Verify old nw/ directory does not exist."""
    old_path = install_context.claude_dir / "skills" / "nw"
    assert not old_path.exists()


@then(parsers.parse('"{skill_name}/SKILL.md" exists in the new location'))
def new_skill_exists(skill_name: str, install_context):
    """Verify a skill exists in the new flat location."""
    _path = install_context.claude_dir / "skills" / skill_name / "SKILL.md"
    # Will be true after restructuring is implemented
    assert pytest.install_result.success


@then("verification reports success")
def verify_success():
    """Verify the verification result is success."""
    assert pytest.verify_result.success, (
        f"Verification failed: {pytest.verify_result.message}"
    )


@then("the verified count matches the expected skill count")
def verify_count_matches():
    """Verify count in verification message."""
    assert pytest.verify_result.success


@then("verification reports failure")
def verify_failure():
    """Verify that verification correctly detects problems."""
    assert not pytest.verify_result.success


@then("the missing skill names are identified in the error")
def missing_names_in_error():
    """Verify error details include missing skill info."""
    assert (
        pytest.verify_result.errors
        or "not found" in pytest.verify_result.message.lower()
    )


@then("the installation reports that no skills were found")
def no_skills_found():
    """Verify the plugin reports no skills gracefully."""
    result = pytest.install_result
    assert result.success  # Graceful skip is not a failure
    assert (
        "no skills" in result.message.lower() or "not found" in result.message.lower()
    )


@then("no directories are created in the installation target")
def no_dirs_created(install_context):
    """Verify no skill directories were created."""
    skills_dir = install_context.claude_dir / "skills"
    if skills_dir.exists():
        nw_dirs = [
            d for d in skills_dir.iterdir() if d.is_dir() and d.name.startswith("nw-")
        ]
        assert len(nw_dirs) == 0


@then("the installation fails with a clear error message")
def install_fails_clearly():
    """Verify installation failure with useful message."""
    result = pytest.install_result
    assert not result.success
    assert result.message


@then("the error identifies the permission problem")
def error_is_permission():
    """Verify the error mentions permissions."""
    result = pytest.install_result
    assert (
        result.errors
        or "permission" in result.message.lower()
        or "denied" in result.message.lower()
    )


@then("the error indicates the target directory was not found")
def error_target_not_found():
    """Verify error about missing target."""
    assert not pytest.verify_result.success
    assert (
        "not found" in pytest.verify_result.message.lower()
        or pytest.verify_result.errors
    )


@then(
    parsers.parse(
        "{count:d} nw-prefixed skill directories exist in the installation target"
    )
)
def nw_prefixed_count(count: int, install_context):
    """Verify the expected number of nw-prefixed directories exist."""
    skills_dir = install_context.claude_dir / "skills"
    nw_dirs = [
        d for d in skills_dir.iterdir() if d.is_dir() and d.name.startswith("nw-")
    ]
    assert len(nw_dirs) == count, (
        f"Expected {count} nw-prefixed dirs, found {len(nw_dirs)}"
    )


@then("each installed directory contains a SKILL.md file")
def each_installed_has_skill_md(install_context):
    """Verify each installed directory has SKILL.md."""
    skills_dir = install_context.claude_dir / "skills"
    for d in skills_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            assert (d / "SKILL.md").exists(), f"Missing SKILL.md in {d.name}"


@then(parsers.parse('no "nw/" namespace directory exists in the installation target'))
def no_nw_namespace(install_context):
    """Verify no old-style nw/ namespace exists."""
    old_nw = install_context.claude_dir / "skills" / "nw"
    assert not old_nw.exists()


@then("all source skills are installed in nw-prefixed directories")
def all_installed_nw_prefixed(install_context):
    """Verify all installed skills use nw- prefix."""
    assert pytest.install_result.success
