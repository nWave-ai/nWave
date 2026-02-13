"""Tests for agent source file YAML frontmatter.

Validates that all 22 agent source files in nWave/agents/nw-*.md
have valid YAML frontmatter with name, description, model fields,
no duplicate --- blocks, and names matching filenames.
"""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = PROJECT_ROOT / "nWave" / "agents"

EXPECTED_AGENTS = sorted(
    [
        "nw-acceptance-designer",
        "nw-acceptance-designer-reviewer",
        "nw-agent-builder",
        "nw-agent-builder-reviewer",
        "nw-data-engineer",
        "nw-data-engineer-reviewer",
        "nw-documentarist",
        "nw-documentarist-reviewer",
        "nw-platform-architect",
        "nw-platform-architect-reviewer",
        "nw-product-discoverer",
        "nw-product-discoverer-reviewer",
        "nw-product-owner",
        "nw-product-owner-reviewer",
        "nw-researcher",
        "nw-researcher-reviewer",
        "nw-software-crafter",
        "nw-software-crafter-reviewer",
        "nw-solution-architect",
        "nw-solution-architect-reviewer",
        "nw-troubleshooter",
        "nw-troubleshooter-reviewer",
    ]
)

REQUIRED_FIELDS = ["name", "description", "model"]


def _parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Returns parsed dict if valid frontmatter found, None otherwise.
    """
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    if "\n---\n" not in content[4:]:
        return None
    end_pos = content.index("\n---\n", 4)
    yaml_block = content[4:end_pos]
    return yaml.safe_load(yaml_block)


def _count_frontmatter_blocks(filepath: Path) -> int:
    """Count number of --- delimited blocks at the start of a file.

    A well-formed file has exactly one block (opening --- and closing ---).
    Duplicate blocks would mean two separate --- ... --- sections.
    """
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return 0
    # Find the first closing ---
    first_close = content.index("\n---\n", 4) if "\n---\n" in content[4:] else None
    if first_close is None:
        return 0
    # Check if there is another --- block immediately after
    after_first = content[first_close + 5 :]  # skip past \n---\n
    # A duplicate block would start with ---\n right after some whitespace
    stripped = after_first.lstrip("\n")
    if stripped.startswith("---\n"):
        return 2
    return 1


# ---------------------------------------------------------------------------
# Acceptance test: all 22 agent files have valid frontmatter
# ---------------------------------------------------------------------------


class TestAgentFrontmatterAcceptance:
    """Acceptance: All 22 agent source files have valid YAML frontmatter."""

    def test_all_agent_files_exist(self):
        """Every expected agent file must exist in the agents directory."""
        missing = [
            name for name in EXPECTED_AGENTS if not (AGENTS_DIR / f"{name}.md").exists()
        ]
        assert not missing, f"Agent files missing: {missing}"

    def test_all_agents_have_frontmatter_with_required_fields(self):
        """Every agent file must have --- frontmatter with name, description, model."""
        no_frontmatter = []
        missing_fields = []

        for agent_name in EXPECTED_AGENTS:
            filepath = AGENTS_DIR / f"{agent_name}.md"
            fm = _parse_frontmatter(filepath)
            if fm is None:
                no_frontmatter.append(agent_name)
                continue
            for field in REQUIRED_FIELDS:
                if field not in fm:
                    missing_fields.append(f"{agent_name}: missing '{field}'")

        assert not no_frontmatter, f"Agents missing frontmatter: {no_frontmatter}"
        assert not missing_fields, "Agents with missing required fields:\n" + "\n".join(
            missing_fields
        )

    def test_no_agent_has_duplicate_frontmatter_blocks(self):
        """No agent file should have duplicate --- blocks."""
        duplicates = [
            name
            for name in EXPECTED_AGENTS
            if _count_frontmatter_blocks(AGENTS_DIR / f"{name}.md") > 1
        ]
        assert not duplicates, f"Agents with duplicate frontmatter blocks: {duplicates}"

    def test_agent_names_in_frontmatter_match_filenames(self):
        """Frontmatter name field must match filename (nw-*.md -> nw-*)."""
        mismatches = []
        for agent_name in EXPECTED_AGENTS:
            filepath = AGENTS_DIR / f"{agent_name}.md"
            fm = _parse_frontmatter(filepath)
            if fm is None:
                continue
            fm_name = fm.get("name", "")
            if fm_name != agent_name:
                mismatches.append(
                    f"{agent_name}: frontmatter name='{fm_name}', expected='{agent_name}'"
                )
        assert not mismatches, "Name mismatches:\n" + "\n".join(mismatches)
