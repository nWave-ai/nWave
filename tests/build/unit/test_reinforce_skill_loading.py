"""Tests for scripts/framework/reinforce_skill_loading.py."""

import pytest

from scripts.framework.reinforce_skill_loading import (
    OnDemandEntry,
    PhaseGroup,
    ReinforcedSection,
    _normalize_skill_name,
    build_reinforced_section,
    extract_frontmatter_skills,
    find_skill_loading_section,
    main,
    parse_skill_table,
    process_agent,
    render_reinforced_section,
    replace_skill_loading_section,
    update_load_directives,
    validate_section,
)


# ---------------------------------------------------------------------------
# Fixtures: mock agent content
# ---------------------------------------------------------------------------
RESEARCHER_CONTENT = """\
---
name: nw-researcher
description: Evidence-driven researcher
model: inherit
tools: Read, Write
maxTurns: 50
skills:
  - nw-research-methodology
  - nw-source-verification
  - nw-operational-safety
  - nw-authoritative-sources
---

# nw-researcher

You are Nova, an Evidence-Driven Knowledge Researcher.

## Core Principles

1. Evidence over assertion.
2. Source verification before citation.

## Skill Loading -- MANDATORY

You MUST load your skill files before beginning any work.

**How**: Use the Read tool to load skill files.
**When**: Load skills at the start of the appropriate phase.
**Rule**: Never skip skill loading.

Load on-demand by phase, not all at once:

| Phase | Load | Trigger |
|-------|------|---------|
| 1 Clarify Scope and Create Skeleton | `research-methodology` | Always -- output template |
| 2 Research-and-Write Cycles | `authoritative-sources`, `operational-safety` | Always -- domain strategies |
| 3 Synthesize and Cross-Reference | `source-verification` | Always -- tier definitions |

Skills path: `~/.claude/skills/nw-{skill-name}/SKILL.md`

## Workflow

### Phase 1: Clarify Scope
Some workflow text here.
"""

CRAFTER_CONTENT = """\
---
name: nw-software-crafter
description: DELIVER wave
model: inherit
tools: Read, Write, Edit, Bash
maxTurns: 50
skills:
  - nw-tdd-methodology
  - nw-progressive-refactoring
  - nw-legacy-refactoring-ddd
  - nw-sc-review-dimensions
  - nw-property-based-testing
  - nw-mikado-method
  - nw-production-safety
  - nw-quality-framework
  - nw-hexagonal-testing
  - nw-test-refactoring-catalog
  - nw-collaboration-and-handoffs
---

# nw-software-crafter

You are Crafty.

## Core Principles

1. Outside-In TDD.

## Skill Loading -- MANDATORY

You MUST load your skill files before beginning any work.

**How**: Use the Read tool to load skill files.
**When**: Load skills at the start of the appropriate phase.
**Rule**: Never skip skill loading.

Load on-demand by phase, not all at once:

| Phase | Load | Trigger |
|-------|------|---------|
| 0 PREPARE | `tdd-methodology`, `quality-framework` | Always -- core methodology |
| 1-2 RED | `hexagonal-testing` | Always -- port/adapter boundary decisions |
| 2 RED_UNIT | `property-based-testing` | AC tagged `@property` or domain invariants |
| 3 GREEN | `production-safety` | Implementation choices |
| 4 COMMIT | `collaboration-and-handoffs` | Handoff context needed |
| Refactor | `progressive-refactoring`, `test-refactoring-catalog` | `/nw-refactor` invocation |
| Refactor | `legacy-refactoring-ddd` | When refactoring legacy code using DDD patterns |
| Review | `review-dimensions` | `/nw-review` invocation |
| Complex refactoring | `mikado-method` | `*mikado` command |

Skills path: `~/.claude/skills/nw-{skill-name}/SKILL.md`

## 5-Phase TDD Workflow

### Phase 0: PREPARE
Load: `tdd-methodology`, `quality-framework` -- read them NOW before proceeding.

### Phase 1: RED (Acceptance)
Load: `hexagonal-testing` -- read it NOW before proceeding.

### Phase 2: RED (Unit)
Load: `property-based-testing` -- read it NOW.

### Phase 3: GREEN
Implement code.

### Phase 4: COMMIT
Commit with message.
"""

NO_TABLE_CONTENT = """\
---
name: nw-business-reviewer
description: Review specialist
model: haiku
tools: Read, Glob, Grep
maxTurns: 20
skills:
  - nw-br-review-criteria
---

# nw-business-reviewer

You are Sentinel.

## Skill Loading -- MANDATORY

You MUST load your skill files before beginning any work.

**How**: Use the Read tool to load skill files.
**Rule**: Never skip skill loading.

## Workflow

### Phase 1: Ingest Document
Do the review.
"""

NO_SKILLS_CONTENT = """\
---
name: nw-empty-agent
description: Agent with no skills
model: inherit
tools: Read
maxTurns: 10
---

# nw-empty-agent

No skill loading section at all.
"""


# ---------------------------------------------------------------------------
# Test: parse_skill_table
# ---------------------------------------------------------------------------
class TestParseSkillTable:
    """Parse the existing Phase|Load|Trigger table."""

    def test_parses_researcher_table_three_rows(self):
        rows = parse_skill_table(RESEARCHER_CONTENT)
        assert len(rows) == 3

    def test_first_row_has_correct_phase(self):
        rows = parse_skill_table(RESEARCHER_CONTENT)
        assert rows[0].phase == "1 Clarify Scope and Create Skeleton"

    def test_first_row_has_correct_skill(self):
        rows = parse_skill_table(RESEARCHER_CONTENT)
        assert rows[0].skill_names == ["research-methodology"]

    def test_second_row_has_multiple_skills(self):
        rows = parse_skill_table(RESEARCHER_CONTENT)
        assert rows[1].skill_names == ["authoritative-sources", "operational-safety"]

    def test_all_rows_marked_always(self):
        rows = parse_skill_table(RESEARCHER_CONTENT)
        assert all(r.is_always for r in rows)

    def test_crafter_has_mixed_triggers(self):
        rows = parse_skill_table(CRAFTER_CONTENT)
        always = [r for r in rows if r.is_always]
        on_demand = [r for r in rows if not r.is_always]
        assert len(always) == 2  # PREPARE and RED
        assert len(on_demand) == 7

    def test_empty_content_returns_no_rows(self):
        rows = parse_skill_table("No table here\n")
        assert rows == []


# ---------------------------------------------------------------------------
# Test: build_reinforced_section for nw-researcher (4 skills, 3 phases)
# ---------------------------------------------------------------------------
class TestBuildResearcherSection:
    """Generate section for nw-researcher: 4 skills, all always-load."""

    @pytest.fixture()
    def section(self):
        fm_skills = [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]
        rows = parse_skill_table(RESEARCHER_CONTENT)
        return build_reinforced_section(fm_skills, rows)

    def test_has_three_phases(self, section: ReinforcedSection):
        assert len(section.phases) == 3

    def test_phase_1_has_one_skill(self, section: ReinforcedSection):
        assert section.phases[0].skills == ["nw-research-methodology"]

    def test_phase_2_has_two_skills(self, section: ReinforcedSection):
        assert set(section.phases[1].skills) == {
            "nw-authoritative-sources",
            "nw-operational-safety",
        }

    def test_phase_3_has_one_skill(self, section: ReinforcedSection):
        assert section.phases[2].skills == ["nw-source-verification"]

    def test_no_on_demand_entries(self, section: ReinforcedSection):
        assert section.on_demand == []


# ---------------------------------------------------------------------------
# Test: build_reinforced_section for nw-software-crafter (11 skills, mixed)
# ---------------------------------------------------------------------------
class TestBuildCrafterSection:
    """Generate section for nw-software-crafter: 11 skills, mixed triggers."""

    @pytest.fixture()
    def section(self):
        fm_skills = [
            "nw-tdd-methodology",
            "nw-progressive-refactoring",
            "nw-legacy-refactoring-ddd",
            "nw-sc-review-dimensions",
            "nw-property-based-testing",
            "nw-mikado-method",
            "nw-production-safety",
            "nw-quality-framework",
            "nw-hexagonal-testing",
            "nw-test-refactoring-catalog",
            "nw-collaboration-and-handoffs",
        ]
        rows = parse_skill_table(CRAFTER_CONTENT)
        return build_reinforced_section(fm_skills, rows)

    def test_has_two_always_phases(self, section: ReinforcedSection):
        assert len(section.phases) == 2

    def test_prepare_phase_skills(self, section: ReinforcedSection):
        assert set(section.phases[0].skills) == {
            "nw-tdd-methodology",
            "nw-quality-framework",
        }

    def test_red_phase_skill(self, section: ReinforcedSection):
        assert section.phases[1].skills == ["nw-hexagonal-testing"]

    def test_on_demand_count(self, section: ReinforcedSection):
        # 11 total - 3 always = 8 on-demand
        assert len(section.on_demand) == 8

    def test_all_11_skills_placed(self, section: ReinforcedSection):
        all_placed = set()
        for pg in section.phases:
            all_placed.update(pg.skills)
        for od in section.on_demand:
            all_placed.add(od.skill_name)
        assert len(all_placed) == 11


# ---------------------------------------------------------------------------
# Test: render_reinforced_section produces correct markdown
# ---------------------------------------------------------------------------
class TestRenderReinforcedSection:
    """Render section to markdown text."""

    def test_starts_with_preamble(self):
        section = ReinforcedSection(
            phases=[PhaseGroup("Startup", ["nw-alpha"])],
            on_demand=[],
            all_skills=["nw-alpha"],
        )
        rendered = render_reinforced_section(section)
        assert rendered.startswith("## Skill Loading -- MANDATORY")

    def test_contains_checkpoint_instructions(self):
        section = ReinforcedSection(
            phases=[PhaseGroup("Startup", ["nw-alpha"])],
            on_demand=[],
            all_skills=["nw-alpha"],
        )
        rendered = render_reinforced_section(section)
        assert "[SKILL LOADED]" in rendered
        assert "[SKILL MISSING]" in rendered

    def test_contains_literal_path(self):
        section = ReinforcedSection(
            phases=[PhaseGroup("Setup", ["nw-research-methodology"])],
            on_demand=[],
            all_skills=["nw-research-methodology"],
        )
        rendered = render_reinforced_section(section)
        assert "`~/.claude/skills/nw-research-methodology/SKILL.md`" in rendered

    def test_on_demand_table_rendered(self):
        section = ReinforcedSection(
            phases=[],
            on_demand=[
                OnDemandEntry("nw-mikado-method", "`*mikado` command"),
            ],
            all_skills=["nw-mikado-method"],
        )
        rendered = render_reinforced_section(section)
        assert "### On-Demand (load only when triggered)" in rendered
        assert "| `~/.claude/skills/nw-mikado-method/SKILL.md`" in rendered

    def test_no_template_variables_in_paths(self):
        """Skill paths contain no template variables (preamble {skill-name} is ok)."""
        section = ReinforcedSection(
            phases=[PhaseGroup("Phase1", ["nw-alpha", "nw-beta"])],
            on_demand=[OnDemandEntry("nw-gamma", "when needed")],
            all_skills=["nw-alpha", "nw-beta", "nw-gamma"],
        )
        rendered = render_reinforced_section(section)
        # Extract only lines containing paths (backtick-delimited)
        path_lines = [ln for ln in rendered.splitlines() if "~/.claude/skills/" in ln]
        for line in path_lines:
            assert "{skill-name}" not in line
            assert "{agent-name}" not in line
        # No {agent-name} anywhere
        assert "{agent-name}" not in rendered


# ---------------------------------------------------------------------------
# Test: find_skill_loading_section
# ---------------------------------------------------------------------------
class TestFindSkillLoadingSection:
    """Find the line range of the skill loading section."""

    def test_finds_researcher_section(self):
        bounds = find_skill_loading_section(RESEARCHER_CONTENT)
        assert bounds is not None
        start, end = bounds
        lines = RESEARCHER_CONTENT.splitlines()
        assert "Skill Loading" in lines[start]
        # End should be at "## Workflow"
        assert "## Workflow" in lines[end]

    def test_returns_none_for_no_section(self):
        bounds = find_skill_loading_section("# No skill loading\n\nJust text.\n")
        assert bounds is None

    def test_section_extends_to_eof_if_last(self):
        content = "# Agent\n\n## Skill Loading -- MANDATORY\n\nSome content.\n"
        bounds = find_skill_loading_section(content)
        assert bounds is not None
        _, end = bounds
        assert end == len(content.splitlines())


# ---------------------------------------------------------------------------
# Test: replace_skill_loading_section
# ---------------------------------------------------------------------------
class TestReplaceSkillLoadingSection:
    """Replace the section between ## Skill Loading and next ##."""

    def test_replaces_section_preserving_surrounding(self):
        new_section = "## Skill Loading -- MANDATORY\n\nNew content here."
        result = replace_skill_loading_section(RESEARCHER_CONTENT, new_section)
        assert "New content here." in result
        assert "## Workflow" in result
        assert "## Core Principles" in result

    def test_old_prose_removed(self):
        new_section = "## Skill Loading -- MANDATORY\n\nNew content."
        result = replace_skill_loading_section(RESEARCHER_CONTENT, new_section)
        assert "Skills path:" not in result
        assert "{skill-name}" not in result


# ---------------------------------------------------------------------------
# Test: validation
# ---------------------------------------------------------------------------
class TestValidation:
    """Validate generated sections."""

    def test_valid_section_passes(self, tmp_path):
        # Create mock skill directories
        for name in ["nw-alpha", "nw-beta"]:
            (tmp_path / name).mkdir()

        rendered = (
            "## Skill Loading -- MANDATORY\n"
            "- `~/.claude/skills/nw-alpha/SKILL.md`\n"
            "- `~/.claude/skills/nw-beta/SKILL.md`\n"
        )
        result = validate_section(
            "test-agent",
            rendered,
            ["nw-alpha", "nw-beta"],
            original_line_count=5,
            skills_dir=tmp_path,
        )
        assert result.ok

    def test_missing_skill_is_error(self, tmp_path):
        rendered = (
            "## Skill Loading -- MANDATORY\n- `~/.claude/skills/nw-alpha/SKILL.md`\n"
        )
        result = validate_section(
            "test-agent",
            rendered,
            ["nw-alpha", "nw-beta"],
            original_line_count=3,
            skills_dir=tmp_path,
        )
        assert not result.ok
        assert any("nw-beta" in e and "not found" in e for e in result.errors)

    def test_duplicate_skill_is_error(self, tmp_path):
        (tmp_path / "nw-alpha").mkdir()
        rendered = (
            "## Skill Loading -- MANDATORY\n"
            "- `~/.claude/skills/nw-alpha/SKILL.md`\n"
            "- `~/.claude/skills/nw-alpha/SKILL.md`\n"
        )
        result = validate_section(
            "test-agent",
            rendered,
            ["nw-alpha"],
            original_line_count=3,
            skills_dir=tmp_path,
        )
        assert not result.ok
        assert any("appears 2 times" in e for e in result.errors)

    def test_template_variable_is_error(self, tmp_path):
        # Build a realistic rendered section with preamble + a bad path line
        rendered = (
            "## Skill Loading -- MANDATORY\n"
            "\n"
            "Your FIRST action before any other work: load skills using the Read tool.\n"
            "Each skill MUST be loaded by reading its exact file path.\n"
            "After loading each skill, output: `[SKILL LOADED] {skill-name}`\n"
            "If a file is not found, output: `[SKILL MISSING] {skill-name}` and continue.\n"
            "\n"
            "### Phase 1: Startup\n"
            "\n"
            "Read these files NOW:\n"
            "- `~/.claude/skills/{skill-name}/SKILL.md`\n"
        )
        result = validate_section(
            "test-agent", rendered, [], original_line_count=5, skills_dir=tmp_path
        )
        assert not result.ok
        assert any("{skill-name}" in e for e in result.errors)

    def test_missing_directory_is_warning(self, tmp_path):
        rendered = "## Skill Loading\n- `~/.claude/skills/nw-alpha/SKILL.md`\n"
        result = validate_section(
            "test-agent",
            rendered,
            ["nw-alpha"],
            original_line_count=2,
            skills_dir=tmp_path,
        )
        # Missing dir is a warning, not an error
        assert result.ok
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Test: no-table agent defaults to Phase 1
# ---------------------------------------------------------------------------
class TestNoTableAgent:
    """Agent with no table puts all skills in Phase 1."""

    def test_builds_single_phase(self):
        fm_skills = ["nw-br-review-criteria"]
        rows = parse_skill_table(NO_TABLE_CONTENT)
        section = build_reinforced_section(fm_skills, rows)
        assert len(section.phases) == 1
        assert section.phases[0].phase_name == "Startup"
        assert section.phases[0].skills == ["nw-br-review-criteria"]


# ---------------------------------------------------------------------------
# Test: extract_frontmatter_skills
# ---------------------------------------------------------------------------
class TestExtractFrontmatterSkills:
    """Extract skills list from YAML frontmatter."""

    def test_extracts_researcher_skills(self):
        skills = extract_frontmatter_skills(RESEARCHER_CONTENT)
        assert skills == [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]

    def test_no_skills_returns_empty(self):
        skills = extract_frontmatter_skills(NO_SKILLS_CONTENT)
        assert skills == []

    def test_no_frontmatter_returns_empty(self):
        skills = extract_frontmatter_skills("Just plain text\n")
        assert skills == []


# ---------------------------------------------------------------------------
# Test: process_agent end-to-end with tmp_path
# ---------------------------------------------------------------------------
class TestProcessAgent:
    """End-to-end processing of agent files."""

    def test_researcher_produces_changed_output(self, tmp_path):
        agent_file = tmp_path / "nw-researcher.md"
        agent_file.write_text(RESEARCHER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]:
            (skills_dir / name).mkdir()

        result = process_agent(agent_file, skills_dir=skills_dir)
        assert result.changed
        assert result.ok

    def test_output_contains_literal_paths(self, tmp_path):
        agent_file = tmp_path / "nw-researcher.md"
        agent_file.write_text(RESEARCHER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]:
            (skills_dir / name).mkdir()

        result = process_agent(agent_file, skills_dir=skills_dir)
        assert (
            "`~/.claude/skills/nw-research-methodology/SKILL.md`" in result.new_content
        )

    def test_output_removes_old_prose(self, tmp_path):
        agent_file = tmp_path / "nw-researcher.md"
        agent_file.write_text(RESEARCHER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]:
            (skills_dir / name).mkdir()

        result = process_agent(agent_file, skills_dir=skills_dir)
        assert "Skills path:" not in result.new_content

    def test_no_skills_agent_unchanged(self, tmp_path):
        agent_file = tmp_path / "nw-empty-agent.md"
        agent_file.write_text(NO_SKILLS_CONTENT, encoding="utf-8")
        result = process_agent(agent_file)
        assert not result.changed

    def test_crafter_on_demand_table_present(self, tmp_path):
        agent_file = tmp_path / "nw-software-crafter.md"
        agent_file.write_text(CRAFTER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-tdd-methodology",
            "nw-progressive-refactoring",
            "nw-legacy-refactoring-ddd",
            "nw-sc-review-dimensions",
            "nw-property-based-testing",
            "nw-mikado-method",
            "nw-production-safety",
            "nw-quality-framework",
            "nw-hexagonal-testing",
            "nw-test-refactoring-catalog",
            "nw-collaboration-and-handoffs",
        ]:
            (skills_dir / name).mkdir()

        result = process_agent(agent_file, skills_dir=skills_dir)
        assert "### On-Demand (load only when triggered)" in result.new_content

    def test_crafter_has_load_directive_redundancy(self, tmp_path):
        agent_file = tmp_path / "nw-software-crafter.md"
        agent_file.write_text(CRAFTER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-tdd-methodology",
            "nw-progressive-refactoring",
            "nw-legacy-refactoring-ddd",
            "nw-sc-review-dimensions",
            "nw-property-based-testing",
            "nw-mikado-method",
            "nw-production-safety",
            "nw-quality-framework",
            "nw-hexagonal-testing",
            "nw-test-refactoring-catalog",
            "nw-collaboration-and-handoffs",
        ]:
            (skills_dir / name).mkdir()

        result = process_agent(agent_file, skills_dir=skills_dir)
        # 11 skills >= 5, so Load: directives should be updated
        assert "~/.claude/skills/nw-tdd-methodology/SKILL.md" in result.new_content


# ---------------------------------------------------------------------------
# D1: Test _normalize_skill_name
# ---------------------------------------------------------------------------
class TestNormalizeSkillName:
    """Direct tests for skill name normalization logic."""

    FRONTMATTER = [
        "nw-research-methodology",
        "nw-source-verification",
        "nw-rr-critique-dimensions",
        "nw-tdd-methodology",
        "nw-hexagonal-testing",
        "nw-collaboration-and-handoffs",
    ]

    def test_exact_match_returns_unchanged(self):
        result = _normalize_skill_name("nw-research-methodology", self.FRONTMATTER)
        assert result == "nw-research-methodology"

    def test_prefix_addition(self):
        result = _normalize_skill_name("research-methodology", self.FRONTMATTER)
        assert result == "nw-research-methodology"

    def test_slash_path_with_prefix_abbreviation(self):
        result = _normalize_skill_name(
            "researcher-reviewer/critique-dimensions", self.FRONTMATTER
        )
        assert result == "nw-rr-critique-dimensions"

    def test_recursive_slash_path_handling(self):
        fm = ["nw-deep-nested-skill"]
        result = _normalize_skill_name("a/b/deep-nested-skill", fm)
        # Only the last component after the final "/" is used
        assert result == "nw-deep-nested-skill"

    def test_suffix_matching_with_abbreviated_prefix(self):
        result = _normalize_skill_name("critique-dimensions", self.FRONTMATTER)
        assert result == "nw-rr-critique-dimensions"

    def test_fallback_to_nw_prefix_convention(self):
        result = _normalize_skill_name("nonexistent-skill", self.FRONTMATTER)
        assert result == "nw-nonexistent-skill"

    def test_first_match_returned_when_multiple_suffixes_match(self):
        fm = ["nw-alpha-testing", "nw-beta-testing"]
        result = _normalize_skill_name("testing", fm)
        assert result == "nw-alpha-testing"

    def test_no_match_returns_nw_prefixed(self):
        result = _normalize_skill_name("completely-unknown", [])
        assert result == "nw-completely-unknown"

    def test_hyphenated_suffix_match(self):
        result = _normalize_skill_name("collaboration-and-handoffs", self.FRONTMATTER)
        assert result == "nw-collaboration-and-handoffs"


# ---------------------------------------------------------------------------
# D2: Test update_load_directives
# ---------------------------------------------------------------------------
class TestUpdateLoadDirectives:
    """Direct tests for Load: directive path expansion."""

    FRONTMATTER = [
        "nw-tdd-methodology",
        "nw-quality-framework",
        "nw-hexagonal-testing",
        "nw-property-based-testing",
        "nw-production-safety",
    ]

    def test_single_skill_expanded_to_full_path(self):
        content = "Load: `tdd-methodology`\n"
        result = update_load_directives(
            content, self.FRONTMATTER, apply_redundancy=True
        )
        assert "Load: `~/.claude/skills/nw-tdd-methodology/SKILL.md`" in result

    def test_multiple_skills_both_expanded(self):
        content = "Load: `tdd-methodology`, `quality-framework`\n"
        result = update_load_directives(
            content, self.FRONTMATTER, apply_redundancy=True
        )
        assert "~/.claude/skills/nw-tdd-methodology/SKILL.md`" in result
        assert "~/.claude/skills/nw-quality-framework/SKILL.md`" in result

    def test_suffix_preserved_after_expansion(self):
        content = "Load: `tdd-methodology` -- read them NOW before proceeding.\n"
        result = update_load_directives(
            content, self.FRONTMATTER, apply_redundancy=True
        )
        assert "-- read them NOW before proceeding." in result
        assert "~/.claude/skills/nw-tdd-methodology/SKILL.md`" in result

    def test_indentation_preserved(self):
        content = "    Load: `tdd-methodology`\n"
        result = update_load_directives(
            content, self.FRONTMATTER, apply_redundancy=True
        )
        assert result.startswith("    Load:")

    def test_noop_when_redundancy_disabled(self):
        content = "Load: `tdd-methodology`\n"
        result = update_load_directives(
            content, self.FRONTMATTER, apply_redundancy=False
        )
        assert result == content


# ---------------------------------------------------------------------------
# D4: Test replace_skill_loading_section format preservation
# ---------------------------------------------------------------------------
class TestReplacePreservesFormat:
    """Verify trailing newlines and blank line separators."""

    def test_blank_line_between_new_section_and_next_header(self):
        content = (
            "# Agent\n"
            "\n"
            "## Skill Loading -- MANDATORY\n"
            "\n"
            "Old content.\n"
            "\n"
            "## Workflow\n"
            "\n"
            "Phase 1 stuff.\n"
        )
        new_section = "## Skill Loading -- MANDATORY\n\nNew content here."
        result = replace_skill_loading_section(content, new_section)
        lines = result.splitlines()
        workflow_idx = next(
            i for i, ln in enumerate(lines) if ln.startswith("## Workflow")
        )
        assert lines[workflow_idx - 1] == "", "Expected blank line before ## Workflow"

    def test_trailing_newline_preserved_when_present(self):
        content = "# Agent\n\n## Skill Loading\n\nOld.\n\n## Next\n\nEnd.\n"
        new_section = "## Skill Loading -- MANDATORY\n\nNew."
        result = replace_skill_loading_section(content, new_section)
        assert result.endswith("\n")

    def test_no_trailing_newline_when_absent(self):
        content = "# Agent\n\n## Skill Loading\n\nOld.\n\n## Next\n\nEnd."
        new_section = "## Skill Loading -- MANDATORY\n\nNew."
        result = replace_skill_loading_section(content, new_section)
        assert not result.endswith("\n")

    def test_new_section_ending_with_blank_no_double_blank(self):
        content = "# Agent\n\n## Skill Loading\n\nOld.\n\n## Next\n\nEnd.\n"
        new_section = "## Skill Loading -- MANDATORY\n\nNew.\n"
        result = replace_skill_loading_section(content, new_section)
        # Should not have double blank lines before ## Next
        assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# D5: Test dry-run safety
# ---------------------------------------------------------------------------
class TestDryRunSafety:
    """Verify process_agent returns results without writing, and main respects --apply."""

    def test_process_agent_does_not_write_file(self, tmp_path):
        agent_file = tmp_path / "nw-researcher.md"
        agent_file.write_text(RESEARCHER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]:
            (skills_dir / name).mkdir()

        original_text = agent_file.read_text(encoding="utf-8")
        result = process_agent(agent_file, skills_dir=skills_dir)
        assert result.changed
        # File on disk must remain untouched
        assert agent_file.read_text(encoding="utf-8") == original_text

    def test_main_dry_run_does_not_write(self, tmp_path, monkeypatch):
        agent_file = tmp_path / "nw-researcher.md"
        agent_file.write_text(RESEARCHER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]:
            (skills_dir / name).mkdir()

        import scripts.framework.reinforce_skill_loading as mod

        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path)
        monkeypatch.setattr(mod, "SKILLS_DIR", skills_dir)

        original_text = agent_file.read_text(encoding="utf-8")
        exit_code = main([])  # no --apply flag
        assert exit_code == 0
        # File must remain unchanged
        assert agent_file.read_text(encoding="utf-8") == original_text

    def test_main_apply_writes_file(self, tmp_path, monkeypatch):
        agent_file = tmp_path / "nw-researcher.md"
        agent_file.write_text(RESEARCHER_CONTENT, encoding="utf-8")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in [
            "nw-research-methodology",
            "nw-source-verification",
            "nw-operational-safety",
            "nw-authoritative-sources",
        ]:
            (skills_dir / name).mkdir()

        import scripts.framework.reinforce_skill_loading as mod

        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path)
        monkeypatch.setattr(mod, "SKILLS_DIR", skills_dir)

        original_text = agent_file.read_text(encoding="utf-8")
        exit_code = main(["--apply"])
        assert exit_code == 0
        # File must be different after --apply
        assert agent_file.read_text(encoding="utf-8") != original_text
