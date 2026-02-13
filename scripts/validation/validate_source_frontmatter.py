#!/usr/bin/env python3
"""Validate YAML frontmatter in agent and command source files.

Checks that all agent files (nWave/agents/nw-*.md) have frontmatter with
name, description, model fields, and all command files (nWave/tasks/nw/*.md,
excluding legacy/) have frontmatter with description field.

Exits non-zero if any file fails validation.

Usage:
    python scripts/validation/validate_source_frontmatter.py
    python scripts/validation/validate_source_frontmatter.py --project-root /path/to/repo
"""

import argparse
import sys
from pathlib import Path

import yaml


AGENT_REQUIRED_FIELDS = ["name", "description", "model"]
COMMAND_REQUIRED_FIELDS = ["description"]


def parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Returns parsed dict if valid frontmatter found, None otherwise.
    """
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    rest = content[4:]
    if "\n---\n" not in rest:
        # Also check if file ends with \n---\n or \n--- at EOF
        if not rest.endswith("\n---"):
            return None
        yaml_block = rest[:-4]
    else:
        end_pos = content.index("\n---\n", 4)
        yaml_block = content[4:end_pos]
    try:
        parsed = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def validate_agent_file(filepath: Path) -> list[str]:
    """Validate a single agent file. Returns list of error messages."""
    errors = []
    fm = parse_frontmatter(filepath)
    if fm is None:
        errors.append(f"{filepath.name}: missing or invalid YAML frontmatter")
        return errors
    for field in AGENT_REQUIRED_FIELDS:
        if field not in fm or fm[field] is None:
            errors.append(f"{filepath.name}: missing required field '{field}'")
    return errors


def validate_command_file(filepath: Path) -> list[str]:
    """Validate a single command file. Returns list of error messages."""
    errors = []
    fm = parse_frontmatter(filepath)
    if fm is None:
        errors.append(f"{filepath.name}: missing or invalid YAML frontmatter")
        return errors
    for field in COMMAND_REQUIRED_FIELDS:
        if field not in fm or fm[field] is None:
            errors.append(f"{filepath.name}: missing required field '{field}'")
    return errors


def validate_project(project_root: Path) -> list[str]:
    """Validate all agent and command source files under project_root.

    Returns a list of error strings. Empty list means all files are valid.
    """
    errors = []

    # Validate agents
    agents_dir = project_root / "nWave" / "agents"
    if agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("nw-*.md")):
            errors.extend(validate_agent_file(agent_file))

    # Validate commands (exclude legacy/ subdirectory)
    commands_dir = project_root / "nWave" / "tasks" / "nw"
    if commands_dir.is_dir():
        for cmd_file in sorted(commands_dir.glob("*.md")):
            errors.extend(validate_command_file(cmd_file))

    return errors


def main() -> int:
    """Main entry point. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Validate YAML frontmatter in agent and command source files."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(),
        help="Project root directory (default: current directory)",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()

    agents_dir = project_root / "nWave" / "agents"
    commands_dir = project_root / "nWave" / "tasks" / "nw"

    agent_count = len(list(agents_dir.glob("nw-*.md"))) if agents_dir.is_dir() else 0
    command_count = len(list(commands_dir.glob("*.md"))) if commands_dir.is_dir() else 0

    print(
        f"Validating frontmatter: {agent_count} agent files, {command_count} command files"
    )

    errors = validate_project(project_root)

    if errors:
        print(f"\nFAILED: {len(errors)} validation error(s):")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"PASSED: All {agent_count} agents and {command_count} commands have valid frontmatter"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
