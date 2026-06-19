"""
Milestone 2 Acceptance Tests: Colliding Skill Name Resolution.

Scenarios are marked @skip and enabled one at a time as steps are implemented.

Driving ports: Naming convention logic, agent frontmatter validation
"""

from pathlib import Path

import yaml
from pytest_bdd import scenario


# ---------------------------------------------------------------------------
# Colliding skills that keep OLD names until step 03-01 renames them.
# These are stored in old-style agent-group directories, not nw-prefixed.
# ---------------------------------------------------------------------------
COLLIDING_SKILLS = frozenset(
    {"critique-dimensions", "review-dimensions", "review-criteria"}
)

# Map colliding skill -> list of agent-group directories where the skill file lives
COLLIDING_SKILL_DIRS = {
    "critique-dimensions": [
        "acceptance-designer",
        "solution-architect",
        "agent-builder",
        "agent-builder-reviewer",
        "platform-architect-reviewer",
        "researcher-reviewer",
        "solution-architect-reviewer",
    ],
    "review-dimensions": [
        "software-crafter",
        "product-owner",
    ],
    "review-criteria": [
        "business-reviewer",
        "data-engineer-reviewer",
        "documentarist-reviewer",
        "platform-architect-reviewer",
        "product-discoverer-reviewer",
        "product-owner-reviewer",
        "troubleshooter-reviewer",
    ],
}


def _project_root() -> Path:
    """Return the nWave project root directory."""
    return Path(__file__).resolve().parents[4]


def _parse_frontmatter_skills(agent_path: Path) -> list[str]:
    """Extract skills list from agent YAML frontmatter, stripping comments."""
    content = agent_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return []
    end = content.index("---", 3)
    frontmatter_text = content[3:end]
    frontmatter = yaml.safe_load(frontmatter_text)
    return frontmatter.get("skills", []) or []


def _has_frontmatter_comments(agent_path: Path) -> list[str]:
    """Return any comment lines found in the skills: section of frontmatter."""
    content = agent_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return []
    end = content.index("---", 3)
    frontmatter_text = content[3:end]
    comments = []
    in_skills = False
    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("skills:"):
            in_skills = True
            continue
        if in_skills:
            if (
                stripped
                and not stripped.startswith("-")
                and not stripped.startswith("#")
            ):
                break
            if "#" in stripped:
                comments.append(stripped)
    return comments


@scenario(
    "milestone-2-colliding-skills.feature",
    "Audit identifies all naming collisions",
)
def test_audit_collisions():
    """Audit detects all 3 collision groups."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Audit counts all skill files",
)
def test_audit_count():
    """Audit finds all 109 skills."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Audit detects cross-agent skill references",
)
def test_audit_cross_refs():
    """Audit maps cross-agent skill references."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Audit flags orphan skills with no agent reference",
)
def test_audit_orphans():
    """Audit flags unreferenced skills."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Colliding skills receive agent-abbreviation prefix",
)
def test_naming_collision_prefix():
    """Colliding skills get agent abbreviation prefix."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "All 16 colliding skills receive unique names",
)
def test_naming_all_collisions():
    """All 16 collisions resolved with unique names."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Non-colliding skills retain simple nw-prefix",
)
def test_naming_non_colliding():
    """Non-colliding skills get simple nw- prefix."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "All 109 target directory names are unique",
)
def test_naming_all_unique():
    """All 109 names are unique."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Every skill directory name starts with nw-prefix",
)
def test_naming_nw_prefix():
    """All directories start with nw-."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Renamed skill reference updated in agent frontmatter",
)
def test_frontmatter_updated():
    """Renamed skill reference updated."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Non-colliding skill references remain unchanged",
)
def test_frontmatter_unchanged():
    """Non-colliding references preserved."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "All frontmatter skill references resolve to existing directories",
)
def test_frontmatter_all_resolve():
    """US-04: BDD scenario — see direct tests below for real validation."""
    pass


def test_all_frontmatter_skills_use_nw_prefix():
    """US-04: Every skill in agent frontmatter starts with nw-.

    After step 03-01, all skills (including former collisions) use nw- prefix.
    """
    root = _project_root()
    agents_dir = root / "nWave" / "agents"
    violations = []

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        skills = _parse_frontmatter_skills(agent_file)
        for skill in skills:
            if not skill.startswith("nw-"):
                violations.append(f"{agent_file.name}: '{skill}' missing nw- prefix")

    assert violations == [], (
        f"Found {len(violations)} skills without nw- prefix:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_all_frontmatter_skills_resolve_to_existing_dirs():
    """US-04: Every skill reference has a matching directory in nWave/skills/.

    After step 03-01, all skills (including former collisions) resolve uniformly
    as nWave/skills/{skill-name}/ directories.
    """
    root = _project_root()
    agents_dir = root / "nWave" / "agents"
    skills_dir = root / "nWave" / "skills"
    dangling = []

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        skills = _parse_frontmatter_skills(agent_file)
        for skill in skills:
            skill_path = skills_dir / skill
            if not skill_path.is_dir():
                dangling.append(f"{agent_file.name}: '{skill}' -> {skill_path}")

    assert dangling == [], (
        f"Found {len(dangling)} dangling skill references:\n"
        + "\n".join(f"  - {d}" for d in dangling)
    )


def test_no_cross_reference_comments_in_frontmatter():
    """US-04: No cross-reference comments remain in agent frontmatter skills lists."""
    root = _project_root()
    agents_dir = root / "nWave" / "agents"
    agents_with_comments = []

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        comments = _has_frontmatter_comments(agent_file)
        if comments:
            agents_with_comments.append(f"{agent_file.name}: {comments}")

    assert agents_with_comments == [], (
        f"Found cross-reference comments in {len(agents_with_comments)} agents:\n"
        + "\n".join(f"  - {a}" for a in agents_with_comments)
    )


# ---------------------------------------------------------------------------
# Step 03-01: Direct acceptance tests for colliding skill resolution
# ---------------------------------------------------------------------------

# The 16 expected collision-resolved directory names (nw-{abbrev}-{skill})
EXPECTED_COLLISION_DIRS = frozenset(
    {
        # critique-dimensions (7)
        "nw-ad-critique-dimensions",
        "nw-ab-critique-dimensions",
        "nw-abr-critique-dimensions",
        "nw-par-critique-dimensions",
        "nw-rr-critique-dimensions",
        "nw-sa-critique-dimensions",
        "nw-sar-critique-dimensions",
        # review-dimensions (2)
        "nw-sc-review-dimensions",
        "nw-po-review-dimensions",
        # review-criteria (7)
        "nw-der-review-criteria",
        "nw-dr-review-criteria",
        "nw-par-review-criteria",
        "nw-pdr-review-criteria",
        "nw-por-review-criteria",
        "nw-tr-review-criteria",
        "nw-br-review-criteria",
    }
)

# Map each collision-resolved name to the agent that should reference it
COLLISION_DIR_TO_AGENTS = {
    "nw-ad-critique-dimensions": [
        "nw-acceptance-designer",
        "nw-acceptance-designer-reviewer",
    ],
    "nw-ab-critique-dimensions": ["nw-agent-builder"],
    "nw-abr-critique-dimensions": ["nw-agent-builder-reviewer"],
    "nw-par-critique-dimensions": ["nw-platform-architect-reviewer"],
    "nw-rr-critique-dimensions": ["nw-researcher-reviewer"],
    "nw-sa-critique-dimensions": ["nw-solution-architect"],
    "nw-sar-critique-dimensions": ["nw-solution-architect-reviewer"],
    "nw-sc-review-dimensions": [
        "nw-software-crafter",
        "nw-software-crafter-reviewer",
        "nw-functional-software-crafter",
    ],
    "nw-po-review-dimensions": ["nw-product-owner", "nw-product-owner-reviewer"],
    "nw-der-review-criteria": ["nw-data-engineer-reviewer"],
    "nw-dr-review-criteria": ["nw-documentarist-reviewer"],
    "nw-par-review-criteria": ["nw-platform-architect-reviewer"],
    "nw-pdr-review-criteria": ["nw-product-discoverer-reviewer"],
    "nw-por-review-criteria": ["nw-product-owner-reviewer"],
    "nw-tr-review-criteria": ["nw-troubleshooter-reviewer"],
    "nw-br-review-criteria": ["nw-business-reviewer"],
}


def test_all_16_colliding_skills_exist_as_nw_prefixed_dirs():
    """Step 03-01: All 16 colliding skills exist as nw-{abbrev}-{name}/SKILL.md.

    Validates the actual source tree has been restructured.
    Note: 16 not 15 because platform-architect-reviewer owns both
    critique-dimensions and review-criteria.
    """
    root = _project_root()
    skills_dir = root / "nWave" / "skills"
    missing = []

    for expected_dir in sorted(EXPECTED_COLLISION_DIRS):
        dir_path = skills_dir / expected_dir
        if not dir_path.is_dir():
            missing.append(f"{expected_dir}/ directory missing")
        elif not (dir_path / "SKILL.md").is_file():
            missing.append(f"{expected_dir}/SKILL.md missing")

    assert missing == [], (
        f"Missing {len(missing)} collision-resolved skill dirs:\n"
        + "\n".join(f"  - {m}" for m in missing)
    )


def test_old_colliding_agent_group_dirs_removed():
    """Step 03-01: Old agent-group directories no longer exist after migration."""
    root = _project_root()
    skills_dir = root / "nWave" / "skills"
    still_exist = []

    old_dirs = [
        "acceptance-designer",
        "agent-builder",
        "agent-builder-reviewer",
        "platform-architect-reviewer",
        "researcher-reviewer",
        "solution-architect",
        "solution-architect-reviewer",
        "software-crafter",
        "product-owner",
        "data-engineer-reviewer",
        "documentarist-reviewer",
        "product-discoverer-reviewer",
        "product-owner-reviewer",
        "troubleshooter-reviewer",
        "business-reviewer",
    ]
    for old_dir in old_dirs:
        if (skills_dir / old_dir).is_dir():
            still_exist.append(old_dir)

    assert still_exist == [], "Old agent-group directories still exist:\n" + "\n".join(
        f"  - {d}/" for d in still_exist
    )


def test_agent_frontmatter_references_collision_resolved_names():
    """Step 03-01: All agents reference the collision-resolved skill names.

    No agent should reference bare 'critique-dimensions', 'review-dimensions',
    or 'review-criteria' in their frontmatter skills list.
    """
    root = _project_root()
    agents_dir = root / "nWave" / "agents"
    violations = []

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        skills = _parse_frontmatter_skills(agent_file)
        for skill in skills:
            if skill in COLLIDING_SKILLS:
                violations.append(f"{agent_file.name}: still references bare '{skill}'")

    assert violations == [], (
        f"Found {len(violations)} bare colliding skill references:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_all_skill_dirs_start_with_nw_prefix():
    """Step 03-01: Every skill directory in nWave/skills/ starts with nw-."""
    root = _project_root()
    skills_dir = root / "nWave" / "skills"
    violations = []

    for d in sorted(skills_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("nw-"):
            violations.append(d.name)

    assert violations == [], (
        f"Found {len(violations)} skill dirs without nw- prefix:\n"
        + "\n".join(f"  - {v}/" for v in violations)
    )


@scenario(
    "milestone-2-colliding-skills.feature",
    "Naming convention rejects abbreviation collision",
)
def test_naming_abbrev_collision():
    """Abbreviation collision handled with fallback."""
    pass


@scenario(
    "milestone-2-colliding-skills.feature",
    "Audit reports content difference for same-named skills",
)
def test_audit_content_diff():
    """Content hash comparison detects differences."""
    pass
