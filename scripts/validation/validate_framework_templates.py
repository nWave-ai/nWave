#!/usr/bin/env python3
"""Validate nWave agents, skills, and commands against canonical templates.

Deterministic validation using rules from nWave/templates/validation-schemas.json.
Replaces token-expensive AI-based validation with millisecond-fast script checks.

Pre-commit: runs after YAML validation, before tests.
CI: runs in framework-validation job (Stage 2).

Usage:
    python scripts/validation/validate_framework_templates.py
    python scripts/validation/validate_framework_templates.py --project-root /path/to/repo
    python scripts/validation/validate_framework_templates.py --fix-names  # auto-fix name mismatches
    python scripts/validation/validate_framework_templates.py --verbose    # show all checks, not just failures

Exit codes:
    0 = all checks pass
    1 = errors found (blocks commit/build)
    2 = warnings only (advisory, does not block)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    rule_id: str
    severity: str  # "error" | "warning"
    file: str
    message: str


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def add(self, rule_id: str, severity: str, file: str, message: str) -> None:
        self.findings.append(Finding(rule_id, severity, file, message))


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------


def parse_frontmatter(filepath: Path) -> tuple[dict | None, str]:
    """Extract YAML frontmatter and body from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None, content

    rest = content[4:]
    if "\n---\n" not in rest:
        if rest.endswith("\n---"):
            yaml_block = rest[:-4]
            body = ""
        else:
            return None, content
    else:
        end_pos = content.index("\n---\n", 4)
        yaml_block = content[4:end_pos]
        body = content[end_pos + 5 :]

    try:
        parsed = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return None, content

    if not isinstance(parsed, dict):
        return None, content

    return parsed, body


def count_lines(filepath: Path) -> int:
    """Count non-empty lines in a file."""
    return sum(
        1 for line in filepath.read_text(encoding="utf-8").splitlines() if line.strip()
    )


# ---------------------------------------------------------------------------
# Agent validation
# ---------------------------------------------------------------------------


def validate_agent(filepath: Path, result: ValidationResult) -> None:
    """Validate a single agent file against all A-rules."""
    name = filepath.stem
    is_reviewer = name.endswith("-reviewer")
    fm, body = parse_frontmatter(filepath)
    total_lines = count_lines(filepath)

    # A01: frontmatter present
    if fm is None:
        result.add("A01", "error", name, "Missing or invalid YAML frontmatter")
        return  # can't validate further

    # A02: name matches filename
    if fm.get("name") != name:
        result.add(
            "A02",
            "error",
            name,
            f"Frontmatter name '{fm.get('name')}' != filename '{name}'",
        )

    # A03: line count
    if is_reviewer:
        if total_lines > 170:
            result.add(
                "A03", "warning", name, f"Reviewer {total_lines} lines (limit: 170)"
            )
    elif total_lines > 400:
        result.add(
            "A03", "warning", name, f"Specialist {total_lines} lines (limit: 400)"
        )

    # A04: required sections
    required_patterns = {
        "title": (r"^# nw-[a-z][a-z0-9-]+(-reviewer)?$", "Missing H1 title"),
        "persona": (r"^You are [A-Z]", "Missing persona paragraph ('You are {Name}')"),
        "subagent_mode": (r"In subagent mode", "Missing subagent mode paragraph"),
        "core_principles": (
            r"^## Core Principles",
            "Missing ## Core Principles section",
        ),
        "skill_loading": (r"^## Skill Loading", "Missing ## Skill Loading section"),
        "workflow": (
            r"^## (Workflow|Review Workflow|\d+-Phase)",
            "Missing ## Workflow section",
        ),
    }
    for _section, (pattern, msg) in required_patterns.items():
        if not re.search(pattern, body, re.MULTILINE):
            result.add("A04", "error", name, msg)

    # A05: skill loading imperative
    if "You MUST load your skill files" not in body:
        result.add(
            "A05",
            "error",
            name,
            "Skill loading must use 'You MUST load your skill files'",
        )

    # A06: skills path documented
    if "~/.claude/skills/nw/" not in body:
        result.add("A06", "error", name, "Missing skills path (~/.claude/skills/nw/)")

    # A07: orphan skills (skill in frontmatter but no Load: in body)
    fm_skills = fm.get("skills", []) or []
    for skill in fm_skills:
        if skill not in body:
            result.add(
                "A07",
                "error",
                name,
                f"Skill '{skill}' in frontmatter but not referenced in body",
            )

    # A09: example count
    examples = re.findall(r"^### Example \d+", body, re.MULTILINE)
    if len(examples) < 3:
        result.add(
            "A09", "warning", name, f"Only {len(examples)} examples (minimum: 3)"
        )
    elif len(examples) > 7:
        result.add("A09", "warning", name, f"{len(examples)} examples (maximum: 7)")

    # A11: reviewer model must be haiku
    if is_reviewer and fm.get("model") != "haiku":
        result.add(
            "A11",
            "error",
            name,
            f"Reviewer model must be 'haiku', got '{fm.get('model')}'",
        )

    # A12: reviewer must not have write tools
    if is_reviewer:
        tools = fm.get("tools", "")
        for forbidden in ("Write", "Edit", "Bash"):
            if forbidden in tools:
                result.add(
                    "A12", "error", name, f"Reviewer has forbidden tool: {forbidden}"
                )

    # A13: principles divergence intro
    if (
        "principles diverge from defaults" not in body
        and "principles diverging from defaults" not in body
    ):
        result.add(
            "A13", "warning", name, "Missing 'principles diverge from defaults' intro"
        )

    # A14: subagent mode paragraph with CLARIFICATION_NEEDED
    if "CLARIFICATION_NEEDED" not in body:
        result.add(
            "A14",
            "warning",
            name,
            "Missing CLARIFICATION_NEEDED in subagent mode paragraph",
        )

    # A15: maxTurns set
    if "maxTurns" not in fm:
        result.add("A15", "error", name, "Missing maxTurns in frontmatter")

    # A16: skill loading table
    if (
        "| Phase | Load | Trigger |" not in body
        and "| Phase | Load | Path | Trigger |" not in body
    ):
        result.add(
            "A16", "warning", name, "Missing Phase|Load|Trigger skill loading table"
        )

    # Required frontmatter fields
    for req_field in ("name", "description", "model", "tools"):
        if req_field not in fm or fm[req_field] is None:
            result.add(
                "A01", "error", name, f"Missing required frontmatter field: {req_field}"
            )


# ---------------------------------------------------------------------------
# Skill validation
# ---------------------------------------------------------------------------


def validate_skill(filepath: Path, result: ValidationResult) -> None:
    """Validate a single skill file against all S-rules."""
    name = filepath.stem
    fm, body = parse_frontmatter(filepath)
    total_lines = count_lines(filepath)

    # S01: frontmatter present
    if fm is None:
        result.add("S01", "error", name, "Missing or invalid YAML frontmatter")
        return

    # S02: name matches filename
    if fm.get("name") != name:
        result.add(
            "S02",
            "error",
            name,
            f"Frontmatter name '{fm.get('name')}' != filename '{name}'",
        )

    # S03: kebab-case name
    if not re.match(r"^[a-z][a-z0-9-]+$", fm.get("name", "")):
        result.add("S03", "error", name, f"Name '{fm.get('name')}' is not kebab-case")

    # S04: description present
    if not fm.get("description"):
        result.add("S04", "error", name, "Missing or empty description")

    # S05: no persona definition
    if re.search(r"^You are [A-Z]", body, re.MULTILINE):
        result.add(
            "S05",
            "warning",
            name,
            "Skill contains persona definition ('You are {Name}') — belongs in agent",
        )

    # S06: no workflow steps (agent-style phase headers with gates)
    # Skills may contain workflow knowledge (e.g. "discovery-workflow") — only flag
    # agent-style phase patterns like "### Phase 1: Name" with "Gate:" markers
    if re.search(r"^### Phase \d+:.*\n.*Gate:", body, re.MULTILINE):
        result.add(
            "S06",
            "warning",
            name,
            "Skill contains agent-style workflow phases with gates — belongs in agent definition",
        )

    # S07: line count range
    if total_lines < 30:
        result.add(
            "S07", "warning", name, f"Skill only {total_lines} lines (minimum: 30)"
        )
    elif total_lines > 400:
        result.add(
            "S07",
            "warning",
            name,
            f"Skill {total_lines} lines (limit: 400) — consider splitting",
        )

    # S08: has at least one H1 title
    h1_matches = re.findall(r"^# .+$", body, re.MULTILINE)
    if len(h1_matches) == 0:
        result.add("S08", "warning", name, "Missing H1 title")

    # S09: only name, description, and optional agent in frontmatter
    allowed_fields = {"name", "description", "agent"}
    extra_fields = set(fm.keys()) - allowed_fields
    if extra_fields:
        result.add(
            "S09", "warning", name, f"Unexpected frontmatter fields: {extra_fields}"
        )


# ---------------------------------------------------------------------------
# Command validation
# ---------------------------------------------------------------------------


def validate_command(filepath: Path, result: ValidationResult) -> None:
    """Validate a single command file against all C-rules."""
    name = filepath.stem
    fm, body = parse_frontmatter(filepath)
    total_lines = count_lines(filepath)

    # C01: frontmatter present
    if fm is None:
        result.add("C01", "error", name, "Missing or invalid YAML frontmatter")
        return

    # C02: description present
    if not fm.get("description"):
        result.add("C02", "error", name, "Missing or empty description")

    # C03: has title
    if not re.search(r"^# .+", body, re.MULTILINE):
        result.add("C03", "warning", name, "Missing H1 title")

    # C05: has overview
    if "## Overview" not in body:
        result.add("C05", "warning", name, "Missing ## Overview section")

    # C07: has success criteria
    if "## Success Criteria" not in body:
        result.add("C07", "warning", name, "Missing ## Success Criteria section")

    # C09: line count range (use 300 as generous max for any command)
    if total_lines > 300:
        result.add("C09", "warning", name, f"Command {total_lines} lines (limit: 300)")

    # C12: kebab-case filename
    if not re.match(r"^[a-z][a-z0-9-]+$", name):
        result.add("C12", "error", name, f"Filename '{name}' is not kebab-case")


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------


def validate_cross_references(
    project_root: Path,
    result: ValidationResult,
) -> None:
    """Check cross-references: agent skills directories exist, skill files exist.

    Skills can live in multiple directories via cross-reference:
    - Own directory: skills/{agent-name}/
    - Paired specialist (for reviewers): skills/{agent-name-without-reviewer}/
    - Any other agent directory (documented via frontmatter comments)
    """
    agents_dir = project_root / "nWave" / "agents"
    skills_dir = project_root / "nWave" / "skills"

    # Build index of ALL skill files across ALL directories
    all_skill_files: dict[str, list[str]] = {}  # skill_name -> [directory_names]
    if skills_dir.is_dir():
        for skill_file in skills_dir.glob("**/*.md"):
            skill_name = skill_file.stem
            dir_name = skill_file.parent.name
            all_skill_files.setdefault(skill_name, []).append(dir_name)

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        fm, _ = parse_frontmatter(agent_file)
        if fm is None:
            continue

        agent_name = fm.get("name", "").replace("nw-", "", 1)
        fm_skills = fm.get("skills", []) or []

        if not fm_skills:
            continue

        # Check skill directory exists (own or paired specialist)
        skill_dir = skills_dir / agent_name
        base_agent = agent_name.replace("-reviewer", "")
        base_dir = skills_dir / base_agent

        if not skill_dir.is_dir() and not base_dir.is_dir():
            result.add(
                "X01",
                "error",
                fm.get("name", agent_file.stem),
                f"No skills directory found: tried 'skills/{agent_name}/' "
                f"and 'skills/{base_agent}/'",
            )
            continue

        # Check each skill file exists somewhere in the skills tree
        for skill_name in fm_skills:
            if skill_name not in all_skill_files:
                result.add(
                    "X02",
                    "error",
                    fm.get("name", agent_file.stem),
                    f"Skill file '{skill_name}.md' not found in any skills directory",
                )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate nWave agents, skills, and commands against canonical templates."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(),
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all checks including passes",
    )
    parser.add_argument(
        "--agents-only",
        action="store_true",
        help="Only validate agent files",
    )
    parser.add_argument(
        "--skills-only",
        action="store_true",
        help="Only validate skill files",
    )
    parser.add_argument(
        "--commands-only",
        action="store_true",
        help="Only validate command files",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    result = ValidationResult()
    validate_all = not (args.agents_only or args.skills_only or args.commands_only)

    # Discover files
    agents_dir = project_root / "nWave" / "agents"
    skills_dir = project_root / "nWave" / "skills"
    commands_dir = project_root / "nWave" / "tasks" / "nw"

    agent_files = sorted(agents_dir.glob("nw-*.md")) if agents_dir.is_dir() else []
    skill_files = sorted(skills_dir.glob("**/*.md")) if skills_dir.is_dir() else []
    command_files = sorted(commands_dir.glob("*.md")) if commands_dir.is_dir() else []

    # Validate
    if validate_all or args.agents_only:
        for f in agent_files:
            validate_agent(f, result)

    if validate_all or args.skills_only:
        for f in skill_files:
            validate_skill(f, result)

    if validate_all or args.commands_only:
        for f in command_files:
            validate_command(f, result)

    if validate_all:
        validate_cross_references(project_root, result)

    # Report
    errors = result.errors
    warnings = result.warnings
    total_files = len(agent_files) + len(skill_files) + len(command_files)

    print(
        f"Validated: {len(agent_files)} agents, {len(skill_files)} skills, {len(command_files)} commands"
    )

    if args.verbose:
        for f in result.findings:
            icon = "ERROR" if f.severity == "error" else "WARN"
            print(f"  [{icon}] {f.rule_id} {f.file}: {f.message}")
    elif errors or warnings:
        for f in errors:
            print(f"  [ERROR] {f.rule_id} {f.file}: {f.message}")
        for f in warnings:
            print(f"  [WARN]  {f.rule_id} {f.file}: {f.message}")

    if errors:
        print(
            f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s) in {total_files} files"
        )
        return 1

    if warnings:
        print(f"\nPASSED with {len(warnings)} warning(s) in {total_files} files")
        return 0

    print(f"\nPASSED: {total_files} files, all checks clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
