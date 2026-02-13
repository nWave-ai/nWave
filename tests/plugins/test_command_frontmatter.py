"""Tests for command source file YAML frontmatter.

Validates that all 18 command source files in nWave/tasks/nw/*.md
have valid YAML frontmatter with description (and optionally argument-hint)
matching the framework-catalog.yaml metadata.
"""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).parent.parent.parent
COMMANDS_DIR = PROJECT_ROOT / "nWave" / "tasks" / "nw"
CATALOG_PATH = PROJECT_ROOT / "nWave" / "framework-catalog.yaml"

EXPECTED_COMMANDS = sorted(
    [
        "deliver",
        "design",
        "devops",
        "diagram",
        "discover",
        "discuss",
        "distill",
        "document",
        "execute",
        "finalize",
        "forge",
        "mikado",
        "mutation-test",
        "refactor",
        "research",
        "review",
        "roadmap",
        "root-why",
    ]
)


def _parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Returns parsed dict if valid frontmatter found, None otherwise.
    """
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    end_index = content.index("\n---\n", 4) if "\n---\n" in content[4:] else None
    if end_index is None:
        # Try end of frontmatter at \n---\n
        return None
    # +4 because we search from position 4, but index is absolute in content[4:]
    end_pos = content.index("\n---\n", 4)
    yaml_block = content[4:end_pos]
    return yaml.safe_load(yaml_block)


def _load_catalog_commands() -> dict:
    """Load command metadata from framework-catalog.yaml."""
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    return catalog.get("commands", {})


# ---------------------------------------------------------------------------
# Acceptance test: all 18 command files have valid frontmatter
# ---------------------------------------------------------------------------


class TestCommandFrontmatterAcceptance:
    """Acceptance: All 18 command source files have valid YAML frontmatter."""

    def test_all_command_files_have_frontmatter(self):
        """Every command file must start with --- YAML frontmatter containing description."""
        missing = []
        invalid = []

        for cmd_name in EXPECTED_COMMANDS:
            filepath = COMMANDS_DIR / f"{cmd_name}.md"
            assert filepath.exists(), f"Command file missing: {filepath}"

            fm = _parse_frontmatter(filepath)
            if fm is None:
                missing.append(cmd_name)
            elif "description" not in fm:
                invalid.append(cmd_name)

        assert not missing, f"Commands missing frontmatter: {missing}"
        assert not invalid, f"Commands with frontmatter but no description: {invalid}"

    def test_catalog_commands_have_matching_descriptions(self):
        """Commands in catalog must have frontmatter description matching catalog."""
        catalog_commands = _load_catalog_commands()
        mismatches = []

        for catalog_key, meta in catalog_commands.items():
            # Convert catalog key (underscore) to filename (hyphen)
            file_name = catalog_key.replace("_", "-")
            filepath = COMMANDS_DIR / f"{file_name}.md"

            if not filepath.exists():
                continue

            fm = _parse_frontmatter(filepath)
            if fm is None:
                mismatches.append(f"{file_name}: no frontmatter")
                continue

            expected_desc = meta.get("description", "")
            actual_desc = fm.get("description", "")
            if actual_desc != expected_desc:
                mismatches.append(
                    f"{file_name}: expected '{expected_desc}', got '{actual_desc}'"
                )

        assert not mismatches, "Description mismatches:\n" + "\n".join(mismatches)

    def test_catalog_commands_with_argument_hint_have_it_in_frontmatter(self):
        """Commands with argument_hint in catalog must have argument-hint in frontmatter."""
        catalog_commands = _load_catalog_commands()
        missing_hints = []

        for catalog_key, meta in catalog_commands.items():
            if "argument_hint" not in meta:
                continue

            file_name = catalog_key.replace("_", "-")
            filepath = COMMANDS_DIR / f"{file_name}.md"

            if not filepath.exists():
                continue

            fm = _parse_frontmatter(filepath)
            if fm is None:
                missing_hints.append(f"{file_name}: no frontmatter")
                continue

            expected_hint = meta["argument_hint"]
            actual_hint = fm.get("argument-hint", "")
            if actual_hint != expected_hint:
                missing_hints.append(
                    f"{file_name}: expected '{expected_hint}', got '{actual_hint}'"
                )

        assert not missing_hints, "argument-hint mismatches:\n" + "\n".join(
            missing_hints
        )
