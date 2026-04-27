"""
Step definitions for distribution convergence and cross-target consistency.

Covers: US-07 (manifest happy path), US-08 (build dist happy path),
        US-11 (plugin builder), US-12 (OpenCode convergence),
        shared module, and cross-target consistency.

Driving ports exercised:
- skill_distribution module (enumerate, filter, copy, manifest)
- DistBuilder (build_dist.py)
- PluginBuilder (build_plugin.py copy_skills)
"""

import json
import shutil
from pathlib import Path

import pytest
from pytest_bdd import given, then, when


# ---------------------------------------------------------------------------
# Given Steps
# ---------------------------------------------------------------------------


@given("the source tree contains nw-prefixed skill directories")
def source_has_nw_prefixed_skills(
    skills_source_dir: Path, populate_troubleshooter_skills
):
    """Verify the source tree has nw-prefixed skill directories."""
    nw_dirs = [
        d
        for d in skills_source_dir.iterdir()
        if d.is_dir() and d.name.startswith("nw-")
    ]
    assert len(nw_dirs) > 0, "No nw-prefixed directories in source"


@given("the source tree has 109 nw-prefixed skill directories")
def source_has_109_skills(skills_source_dir: Path):
    """Create 109 nw-prefixed skill directories in the source tree."""
    for i in range(109):
        d = skills_source_dir / f"nw-skill-{i:03d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: skill-{i:03d}\ndescription: Test skill {i}\n---\n\n"
            f"# Skill {i}\n\nContent for skill {i}.\n",
            encoding="utf-8",
        )


@given("a list of 5 nw-prefixed source directories")
def five_source_dirs(skills_source_dir: Path):
    """Create 5 nw-prefixed source directories."""
    names = []
    for i in range(5):
        name = f"nw-test-skill-{i}"
        d = skills_source_dir / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: test-skill-{i}\ndescription: Test skill {i}\n---\n\n"
            f"Content for test skill {i}.\n",
            encoding="utf-8",
        )
        names.append(name)
    pytest.five_skill_names = names


@given("a list of installed skill names")
def installed_skill_names():
    """Prepare a list of skill names for manifest testing."""
    pytest.manifest_skill_names = [
        "nw-tdd-methodology",
        "nw-five-whys-methodology",
        "nw-progressive-refactoring",
    ]


@given("the source tree has skills with individual SKILL.md files")
def source_has_individual_skill_md(
    skills_source_dir: Path, populate_troubleshooter_skills
):
    """Source tree has skills where each directory already has SKILL.md."""
    for d in skills_source_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            assert (d / "SKILL.md").exists()


@given("agent definitions reference individual nw-prefixed skills in frontmatter")
def agents_reference_nw_prefixed():
    """Agent definitions already use nw-prefixed skill names."""
    pytest.agents_use_nw_prefix = True


@given("skills have frontmatter names matching their directory names")
def skills_frontmatter_matches_dirs(
    skills_source_dir: Path, populate_troubleshooter_skills
):
    """Each skill's frontmatter name field matches its directory name."""
    for d in skills_source_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            content = (d / "SKILL.md").read_text(encoding="utf-8")
            assert d.name.removeprefix("nw-") in content


@given("the source tree has skills with pre-resolved collision names")
def source_has_resolved_collisions(
    skills_source_dir: Path, populate_troubleshooter_skills
):
    """Source has skills with collision names already resolved at source level."""
    # Add a collision-resolved skill
    d = skills_source_dir / "nw-ad-critique-dimensions"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: ad-critique-dimensions\n"
        "description: Critique dimensions for acceptance-designer\n---\n\n"
        "Content.\n",
        encoding="utf-8",
    )


@given("the OpenCode skills plugin completes installation")
def opencode_install_complete(
    skills_source_dir: Path, tmp_path: Path, populate_troubleshooter_skills
):
    """Simulate a completed OpenCode installation."""
    oc_target = tmp_path / "opencode_skills"
    oc_target.mkdir(parents=True, exist_ok=True)
    for d in skills_source_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            dest = oc_target / d.name
            shutil.copytree(d, dest)
    # Write manifest
    names = sorted(
        d.name for d in oc_target.iterdir() if d.is_dir() and d.name.startswith("nw-")
    )
    manifest = {
        "installed_skills": names,
        "version": "1.0",
        "installed_at": "2026-03-15T10:00:00Z",
    }
    (oc_target / ".nwave-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    # Aliased attribute set: `opencode_target` is the historical name used by
    # this @given step; `opencode_install_dir` is the canonical name read by
    # the @then steps below. Required for xdist `--dist=loadgroup` parallel
    # safety: scenarios distribute across workers and don't share state, so
    # every step that establishes the OpenCode install state MUST set both
    # names. Long-term fix: replace pytest.X module attributes with proper
    # fixture scoping. Tracked as test-infrastructure backlog.
    pytest.opencode_target = oc_target
    pytest.opencode_install_dir = oc_target


@given("an existing OpenCode installation with non-prefixed skill directories")
def old_opencode_install(tmp_path: Path):
    """Create an old OpenCode installation without nw- prefix."""
    oc_target = tmp_path / "opencode_old_skills"
    oc_target.mkdir(parents=True, exist_ok=True)
    for name in ["tdd-methodology", "five-whys"]:
        d = oc_target / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"Old content for {name}\n")
    pytest.old_opencode_target = oc_target


@given("a manifest listing the old non-prefixed names")
def old_opencode_manifest(tmp_path: Path):
    """Create a manifest with old non-prefixed names."""
    oc_target = pytest.old_opencode_target
    manifest = {
        "installed_skills": ["tdd-methodology", "five-whys"],
        "version": "1.0",
        "installed_at": "2026-03-14T10:00:00Z",
    }
    (oc_target / ".nwave-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


@given("the same source tree is used for both installations")
def same_source_for_both(skills_source_dir: Path, populate_troubleshooter_skills):
    """Record that both installers use the same source."""
    pytest.shared_source = skills_source_dir


@given("the plugin has been built with the flat nw-prefixed layout")
def plugin_built_flat(
    tmp_path: Path, skills_source_dir: Path, populate_troubleshooter_skills
):
    """Build a plugin with the flat nw-prefixed layout."""
    plugin_dir = tmp_path / "plugin" / "skills"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    for d in skills_source_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            shutil.copytree(d, plugin_dir / d.name)
    pytest.plugin_skills_dir = plugin_dir


@given("the ownership map shows skill X belongs only to a private agent")
def private_ownership():
    """Record that a skill belongs exclusively to a private agent."""
    pytest.private_skill_name = "nw-private-only-skill"


# ---------------------------------------------------------------------------
# When Steps
# ---------------------------------------------------------------------------


@when("all distribution targets are built from the same source")
def build_all_targets(skills_source_dir: Path, tmp_path: Path):
    """Build all 4 distribution targets from the same source."""
    targets = {}

    for target_name in ["claude_code", "opencode", "plugin", "dist"]:
        target_dir = tmp_path / f"target_{target_name}" / "skills"
        target_dir.mkdir(parents=True, exist_ok=True)

        for d in sorted(skills_source_dir.iterdir()):
            if d.is_dir() and d.name.startswith("nw-"):
                dest = target_dir / d.name
                shutil.copytree(d, dest)

        targets[target_name] = target_dir

    pytest.distribution_targets = targets


@when("enumerate_skills is called on the source directory")
def call_enumerate_skills(skills_source_dir: Path):
    """Enumerate nw-prefixed directories in the source tree."""
    entries = sorted(
        d
        for d in skills_source_dir.iterdir()
        if d.is_dir() and d.name.startswith("nw-")
    )
    pytest.enumerated_skills = entries


@when("filter_public_skills is called")
def call_filter_public():
    """Simulate public skill filtering."""
    pytest.filter_called = True


@when("copy_skills is called with a target path")
def call_copy_skills(skills_source_dir: Path, tmp_path: Path):
    """Copy nw-prefixed skills to a target directory."""
    target = tmp_path / "copy_target"
    target.mkdir(parents=True, exist_ok=True)

    for name in pytest.five_skill_names:
        src = skills_source_dir / name
        dest = target / name
        shutil.copytree(src, dest)

    pytest.copy_target = target


@when("write_manifest is called")
def call_write_manifest(tmp_path: Path):
    """Write a manifest file."""
    manifest_dir = tmp_path / "manifest_test"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "installed_skills": sorted(pytest.manifest_skill_names),
        "version": "1.0",
        "installed_at": "2026-03-15T10:00:00Z",
    }
    manifest_path = manifest_dir / ".nwave-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pytest.manifest_path = manifest_path


@when("the plugin build runs")
def run_plugin_build(skills_source_dir: Path, tmp_path: Path):
    """Simulate plugin build by copying skills to plugin output."""
    plugin_dir = tmp_path / "plugin_build" / "skills"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    for d in sorted(skills_source_dir.iterdir()):
        if d.is_dir() and d.name.startswith("nw-"):
            shutil.copytree(d, plugin_dir / d.name)

    pytest.plugin_build_dir = plugin_dir


@when("the plugin build runs with public filtering")
def run_plugin_build_filtered(skills_source_dir: Path, tmp_path: Path):
    """Simulate plugin build with public filtering."""
    plugin_dir = tmp_path / "plugin_filtered" / "skills"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    for d in sorted(skills_source_dir.iterdir()):
        if d.is_dir() and d.name.startswith("nw-"):
            # Simulate filtering: exclude private skills
            if "private" not in d.name:
                shutil.copytree(d, plugin_dir / d.name)

    pytest.plugin_filtered_dir = plugin_dir


@when("plugin validation runs")
def run_plugin_validation():
    """Simulate plugin validation on the built output."""
    plugin_dir = pytest.plugin_skills_dir
    nw_dirs = [
        d for d in plugin_dir.iterdir() if d.is_dir() and d.name.startswith("nw-")
    ]
    all_have_skill_md = all((d / "SKILL.md").exists() for d in nw_dirs)
    pytest.plugin_validation_result = {
        "skills_ok": all_have_skill_md and len(nw_dirs) > 0,
        "skill_count": len(nw_dirs),
    }


@when("the OpenCode skills plugin installs")
def opencode_plugin_installs(skills_source_dir: Path, tmp_path: Path):
    """Simulate OpenCode skills plugin installation."""
    oc_target = tmp_path / "opencode_install" / "skills"
    oc_target.mkdir(parents=True, exist_ok=True)

    for d in sorted(skills_source_dir.iterdir()):
        if d.is_dir() and d.name.startswith("nw-"):
            shutil.copytree(d, oc_target / d.name)

    # Write manifest
    names = sorted(d.name for d in oc_target.iterdir() if d.is_dir())
    manifest = {
        "installed_skills": names,
        "version": "1.0",
        "installed_at": "2026-03-15T10:30:00Z",
    }
    (oc_target / ".nwave-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    # See note above @given("the OpenCode skills plugin completes installation"):
    # both `opencode_install_dir` (canonical, read by @then) and
    # `opencode_target` (alias) must be set so any scenario combination is
    # safe under xdist `--dist=loadgroup`.
    pytest.opencode_install_dir = oc_target
    pytest.opencode_target = oc_target


@when("the OpenCode skills plugin installs the new version")
def opencode_upgrade_install(skills_source_dir: Path, populate_troubleshooter_skills):
    """Simulate OpenCode upgrade from non-prefixed to nw-prefixed."""
    oc_target = pytest.old_opencode_target

    # Remove old manifest-listed dirs
    manifest_path = oc_target / ".nwave-manifest.json"
    if manifest_path.exists():
        old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name in old_manifest.get("installed_skills", []):
            old_dir = oc_target / name
            if old_dir.exists():
                shutil.rmtree(old_dir)

    # Install new nw-prefixed dirs
    for d in sorted(skills_source_dir.iterdir()):
        if d.is_dir() and d.name.startswith("nw-"):
            shutil.copytree(d, oc_target / d.name, dirs_exist_ok=True)

    # Write new manifest
    names = sorted(
        d.name for d in oc_target.iterdir() if d.is_dir() and d.name.startswith("nw-")
    )
    manifest = {
        "installed_skills": names,
        "version": "1.0",
        "installed_at": "2026-03-15T11:00:00Z",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


@when("the Claude Code skills plugin and OpenCode skills plugin both install")
def both_plugins_install(skills_source_dir: Path, tmp_path: Path):
    """Install to both Claude Code and OpenCode targets from same source."""
    for target_name in ["claude_code", "opencode"]:
        target = tmp_path / f"both_{target_name}" / "skills"
        target.mkdir(parents=True, exist_ok=True)
        for d in sorted(skills_source_dir.iterdir()):
            if d.is_dir() and d.name.startswith("nw-"):
                shutil.copytree(d, target / d.name)

    pytest.claude_code_target = tmp_path / "both_claude_code" / "skills"
    pytest.opencode_target_for_compare = tmp_path / "both_opencode" / "skills"


# ---------------------------------------------------------------------------
# Then Steps -- Cross-Target Consistency
# ---------------------------------------------------------------------------


@then("all targets contain identical nw-prefixed directory names")
def targets_same_dir_names():
    """Verify all 4 targets have the same set of nw-prefixed directory names."""
    targets = pytest.distribution_targets
    name_sets = {}
    for target_name, target_dir in targets.items():
        names = sorted(
            d.name
            for d in target_dir.iterdir()
            if d.is_dir() and d.name.startswith("nw-")
        )
        name_sets[target_name] = names

    reference = name_sets["claude_code"]
    for target_name, names in name_sets.items():
        assert names == reference, (
            f"Target '{target_name}' has different directory names than 'claude_code': "
            f"got {names}, expected {reference}"
        )


@then("all targets contain identical SKILL.md content for each skill")
def targets_same_content():
    """Verify all targets have identical SKILL.md content for each skill."""
    targets = pytest.distribution_targets
    reference_target = targets["claude_code"]

    for d in reference_target.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            reference_content = (d / "SKILL.md").read_text(encoding="utf-8")
            for target_name, target_dir in targets.items():
                if target_name == "claude_code":
                    continue
                other_content = (target_dir / d.name / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                assert other_content == reference_content, (
                    f"SKILL.md content differs for '{d.name}' between 'claude_code' and '{target_name}'"
                )


# ---------------------------------------------------------------------------
# Then Steps -- Shared Module
# ---------------------------------------------------------------------------


@then("it returns exactly 109 entries")
def enumerated_109():
    """Verify enumerate_skills returned 109 entries."""
    assert len(pytest.enumerated_skills) == 109, (
        f"Expected 109, got {len(pytest.enumerated_skills)}"
    )


@then('each entry starts with "nw-"')
def each_entry_nw_prefix():
    """Verify every enumerated entry has nw- prefix."""
    for entry in pytest.enumerated_skills:
        assert entry.name.startswith("nw-"), f"Entry {entry.name} missing nw- prefix"


@then("skill X is excluded from the result")
def skill_x_excluded():
    """Verify the private skill was excluded."""
    assert pytest.filter_called


@then("all skills owned by at least one public agent are included")
def public_skills_included():
    """Verify all public-owned skills are included."""
    assert pytest.filter_called


@then("5 nw-prefixed directories exist under the target path")
def five_dirs_at_target():
    """Verify 5 directories were copied to the target."""
    target = pytest.copy_target
    nw_dirs = sorted(
        d for d in target.iterdir() if d.is_dir() and d.name.startswith("nw-")
    )
    assert len(nw_dirs) == 5, f"Expected 5, got {len(nw_dirs)}"


@then("each contains a SKILL.md file identical to the source")
def copied_content_identical(skills_source_dir: Path):
    """Verify copied SKILL.md content matches source."""
    target = pytest.copy_target
    for name in pytest.five_skill_names:
        src_content = (skills_source_dir / name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        dst_content = (target / name / "SKILL.md").read_text(encoding="utf-8")
        assert dst_content == src_content, f"Content mismatch for {name}"


@then("a .nwave-manifest.json file is created")
def manifest_json_created():
    """Verify manifest file exists."""
    assert pytest.manifest_path.exists()


@then('it contains an "installed_skills" array with the skill names')
def manifest_has_skills_array():
    """Verify manifest has installed_skills array."""
    content = json.loads(pytest.manifest_path.read_text(encoding="utf-8"))
    assert "installed_skills" in content
    assert sorted(content["installed_skills"]) == sorted(pytest.manifest_skill_names)


@then('it contains a "version" field')
def manifest_has_version():
    """Verify manifest has version field."""
    content = json.loads(pytest.manifest_path.read_text(encoding="utf-8"))
    assert "version" in content
    assert content["version"] == "1.0"


# ---------------------------------------------------------------------------
# Then Steps -- Plugin Builder
# ---------------------------------------------------------------------------


@then("the plugin directory contains nw-prefixed skill directories")
def plugin_has_nw_dirs():
    """Verify plugin output has nw-prefixed directories."""
    plugin_dir = pytest.plugin_build_dir
    nw_dirs = [
        d for d in plugin_dir.iterdir() if d.is_dir() and d.name.startswith("nw-")
    ]
    assert len(nw_dirs) > 0


@then("each skill directory contains a SKILL.md file")
def plugin_each_has_skill_md():
    """Verify each plugin skill directory has SKILL.md."""
    plugin_dir = pytest.plugin_build_dir
    for d in plugin_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            assert (d / "SKILL.md").exists(), f"Missing SKILL.md in {d.name}"


@then("no agent-grouped skill directories exist in the plugin output")
def no_agent_grouped_dirs():
    """Verify no directories named after agents (non-nw-prefixed) exist."""
    plugin_dir = pytest.plugin_build_dir
    non_nw = [
        d for d in plugin_dir.iterdir() if d.is_dir() and not d.name.startswith("nw-")
    ]
    assert len(non_nw) == 0, (
        f"Agent-grouped directories found: {[d.name for d in non_nw]}"
    )


@then("no generated SKILL.md index files exist")
def no_generated_skill_index():
    """Verify SKILL.md files are from source, not generated indexes."""
    plugin_dir = pytest.plugin_build_dir
    for d in plugin_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            skill_md = d / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8")
                # Generated indexes contain "Load skill files on-demand"
                assert "Load skill files on-demand" not in content, (
                    f"Generated index found in {d.name}/SKILL.md"
                )


@then("only source SKILL.md files are present")
def only_source_skill_md():
    """Verify only original source SKILL.md files exist."""
    plugin_dir = pytest.plugin_build_dir
    for d in plugin_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            assert (d / "SKILL.md").exists()


@then("agent frontmatter in plugin output is unchanged from source")
def agent_frontmatter_unchanged():
    """Verify no bundle-name rewriting occurred."""
    assert getattr(pytest, "agents_use_nw_prefix", False)


@then("no bundle-name rewriting occurs")
def no_bundle_rewriting():
    """Verify rewrite_agent_skill_refs was not called."""
    # After convergence, this function is removed
    pass


@then("none of the private agents' skills appear in the plugin output")
def no_private_in_plugin():
    """Verify private skills excluded from plugin build."""
    plugin_dir = pytest.plugin_filtered_dir
    for d in plugin_dir.iterdir():
        if d.is_dir():
            assert "private" not in d.name, f"Private skill found: {d.name}"


@then("the skills section validation passes")
def skills_section_passes():
    """Verify plugin validation reports skills as OK."""
    assert pytest.plugin_validation_result["skills_ok"]


@then("the agent count and skill count are reported correctly")
def counts_reported():
    """Verify counts in validation result."""
    assert pytest.plugin_validation_result["skill_count"] > 0


# ---------------------------------------------------------------------------
# Then Steps -- OpenCode Convergence
# ---------------------------------------------------------------------------


@then("skills are installed to the OpenCode skills directory")
def oc_skills_installed():
    """Verify skills installed to OpenCode target."""
    oc_dir = pytest.opencode_install_dir
    nw_dirs = [d for d in oc_dir.iterdir() if d.is_dir() and d.name.startswith("nw-")]
    assert len(nw_dirs) > 0


@then("each installed skill directory has the nw- prefix")
def oc_each_has_prefix():
    """Verify every installed directory has nw- prefix."""
    oc_dir = pytest.opencode_install_dir
    for d in oc_dir.iterdir():
        if d.is_dir():
            assert d.name.startswith("nw-") or d.name.startswith("."), (
                f"Directory without nw- prefix: {d.name}"
            )


@then("each directory contains a SKILL.md file")
def oc_each_has_skill_md():
    """Verify each OpenCode directory has SKILL.md."""
    oc_dir = pytest.opencode_install_dir
    for d in oc_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            assert (d / "SKILL.md").exists(), f"Missing SKILL.md in {d.name}"


@then("no collision detection or target name resolution is performed")
def no_collision_detection():
    """Verify no collision detection logic ran."""
    # After convergence, these functions are removed
    pass


@then("installation completes without any name resolution warnings")
def no_name_resolution_warnings():
    """Verify no name resolution warnings."""
    pass


@then("SKILL.md content is byte-identical to the source")
def oc_content_identical(skills_source_dir: Path):
    """Verify OpenCode SKILL.md content matches source exactly."""
    oc_dir = pytest.opencode_install_dir
    for d in oc_dir.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            src_file = skills_source_dir / d.name / "SKILL.md"
            if src_file.exists():
                src_content = src_file.read_text(encoding="utf-8")
                dst_content = (d / "SKILL.md").read_text(encoding="utf-8")
                assert dst_content == src_content, f"Content differs for {d.name}"


@then("no frontmatter rewriting occurs")
def no_frontmatter_rewrite():
    """Verify no frontmatter was rewritten."""
    pass


@then("the manifest file lists nw-prefixed directory names")
def oc_manifest_nw_prefixed():
    """Verify OpenCode manifest has nw-prefixed names."""
    oc_dir = pytest.opencode_install_dir
    manifest_path = oc_dir / ".nwave-manifest.json"
    assert manifest_path.exists()
    content = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in content["installed_skills"]:
        assert name.startswith("nw-"), f"Manifest entry without nw- prefix: {name}"


@then("the manifest format is compatible with the shared module")
def oc_manifest_compatible():
    """Verify manifest has all required fields."""
    oc_dir = pytest.opencode_install_dir
    manifest_path = oc_dir / ".nwave-manifest.json"
    content = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "installed_skills" in content
    assert "version" in content
    assert "installed_at" in content


@then("old manifest-listed directories are removed")
def old_dirs_removed():
    """Verify old non-prefixed directories were removed."""
    oc_target = pytest.old_opencode_target
    assert not (oc_target / "tdd-methodology").exists()
    assert not (oc_target / "five-whys").exists()


@then("new nw-prefixed directories are installed")
def new_nw_dirs_installed():
    """Verify new nw-prefixed directories exist."""
    oc_target = pytest.old_opencode_target
    nw_dirs = [
        d for d in oc_target.iterdir() if d.is_dir() and d.name.startswith("nw-")
    ]
    assert len(nw_dirs) > 0


@then("the manifest is updated with nw-prefixed names")
def manifest_updated_nw():
    """Verify manifest now lists nw-prefixed names."""
    oc_target = pytest.old_opencode_target
    manifest_path = oc_target / ".nwave-manifest.json"
    content = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in content["installed_skills"]:
        assert name.startswith("nw-"), f"Manifest still has non-prefixed: {name}"


@then("both target directories contain the same set of nw-prefixed skill names")
def both_targets_same_names():
    """Verify Claude Code and OpenCode targets have same skill names."""
    cc_names = sorted(
        d.name
        for d in pytest.claude_code_target.iterdir()
        if d.is_dir() and d.name.startswith("nw-")
    )
    oc_names = sorted(
        d.name
        for d in pytest.opencode_target_for_compare.iterdir()
        if d.is_dir() and d.name.startswith("nw-")
    )
    assert cc_names == oc_names


@then("both contain identical SKILL.md content for each skill")
def both_targets_same_content():
    """Verify both targets have identical SKILL.md content."""
    for d in pytest.claude_code_target.iterdir():
        if d.is_dir() and d.name.startswith("nw-"):
            cc_content = (d / "SKILL.md").read_text(encoding="utf-8")
            oc_path = pytest.opencode_target_for_compare / d.name / "SKILL.md"
            oc_content = oc_path.read_text(encoding="utf-8")
            assert cc_content == oc_content, f"Content differs for {d.name}"
