"""Reinforce skill loading sections in agent definitions.

Replaces the prose-based ``## Skill Loading`` sections with literal-path,
imperative-language sections that eliminate LLM path-guessing failures.

See ``docs/analysis/proposal-reinforced-skill-loading.md`` for rationale.

Usage::

    # Dry-run (show what would change)
    python scripts/framework/reinforce_skill_loading.py

    # Apply changes
    python scripts/framework/reinforce_skill_loading.py --apply

    # Single agent
    python scripts/framework/reinforce_skill_loading.py --agent nw-researcher --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Allow running standalone (outside pipenv)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.shared.frontmatter import parse_frontmatter  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SKILLS_BASE = "~/.claude/skills"
AGENTS_DIR = _REPO_ROOT / "nWave" / "agents"
SKILLS_DIR = _REPO_ROOT / "nWave" / "skills"
PREAMBLE_LINES = [
    "## Skill Loading -- MANDATORY",
    "",
    "Your FIRST action before any other work: load skills using the Read tool.",
    "Each skill MUST be loaded by reading its exact file path.",
    "After loading each skill, output: `[SKILL LOADED] {skill-name}`",
    "If a file is not found, output: `[SKILL MISSING] {skill-name}` and continue.",
]

# Regex for the skill loading table rows:
#   | Phase description | `skill-names` | Trigger text |
TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<phase>[^|]+?)\s*\|\s*(?P<skills>[^|]+?)\s*\|\s*(?P<trigger>[^|]+?)\s*\|$"
)

# Matches the header row and separator row of the table
TABLE_HEADER_RE = re.compile(r"^\|\s*Phase\s*\|\s*Load\s*\|\s*Trigger\s*\|$")
TABLE_SEP_RE = re.compile(r"^\|[-\s|]+\|$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class SkillTableRow:
    """A parsed row from the existing skill loading table."""

    phase: str
    skill_names: list[str]
    trigger: str
    is_always: bool


@dataclass
class PhaseGroup:
    """Skills grouped under a phase heading."""

    phase_name: str
    skills: list[str]


@dataclass
class OnDemandEntry:
    """A skill with a conditional trigger."""

    skill_name: str
    trigger: str


@dataclass
class ReinforcedSection:
    """The generated reinforced skill loading section."""

    phases: list[PhaseGroup]
    on_demand: list[OnDemandEntry]
    all_skills: list[str]


@dataclass
class ValidationResult:
    """Result of validating a generated section."""

    agent_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def extract_frontmatter_skills(content: str) -> list[str]:
    """Extract the ``skills:`` list from YAML frontmatter."""
    meta, _ = parse_frontmatter(content)
    if meta is None:
        return []
    skills = meta.get("skills", [])
    if not isinstance(skills, list):
        return []
    return [str(s) for s in skills]


def parse_skill_table(content: str) -> list[SkillTableRow]:
    """Parse the ``| Phase | Load | Trigger |`` table from the Skill Loading section.

    Only scans inside the ``## Skill Loading`` section to avoid picking up
    template-example tables elsewhere in the file.

    Returns an empty list if no table is found.
    """
    # Restrict to skill loading section if present
    bounds = find_skill_loading_section(content)
    if bounds is not None:
        start, end = bounds
        section_lines = content.splitlines()[start:end]
    else:
        section_lines = content.splitlines()

    rows: list[SkillTableRow] = []
    in_table = False

    for line in section_lines:
        stripped = line.strip()
        if TABLE_HEADER_RE.match(stripped):
            in_table = True
            continue
        if in_table and TABLE_SEP_RE.match(stripped):
            continue
        if in_table:
            m = TABLE_ROW_RE.match(stripped)
            if m:
                phase = m.group("phase").strip()
                raw_skills = m.group("skills").strip()
                trigger = m.group("trigger").strip()

                # Parse skill names: remove backticks, split on comma
                skill_names = _parse_skill_names(raw_skills)
                is_always = "always" in trigger.lower()

                rows.append(
                    SkillTableRow(
                        phase=phase,
                        skill_names=skill_names,
                        trigger=trigger,
                        is_always=is_always,
                    )
                )
            else:
                in_table = False

    return rows


def _parse_skill_names(raw: str) -> list[str]:
    """Parse skill names from a table cell like ```name1`, `name2```.

    Handles both short names (``research-methodology``) and full names
    (``nw-research-methodology``).
    """
    # Remove backticks
    cleaned = raw.replace("`", "")
    # Split on comma
    parts = [p.strip() for p in cleaned.split(",")]
    return [p for p in parts if p]


def _normalize_skill_name(name: str, frontmatter_skills: list[str]) -> str:
    """Map a (possibly short) skill name to the full frontmatter skill name.

    Strategy:
    1. If the name is already in frontmatter_skills, return it.
    2. If ``nw-{name}`` is in frontmatter_skills, return that.
    3. If any frontmatter skill ends with ``-{name}`` or contains the name
       as a suffix, return it.
    4. Return ``nw-{name}`` as best guess.
    """
    if name in frontmatter_skills:
        return name

    with_prefix = f"nw-{name}"
    if with_prefix in frontmatter_skills:
        return with_prefix

    # Handle cases like table says "researcher-reviewer/critique-dimensions"
    # but frontmatter has "nw-rr-critique-dimensions"
    # Try suffix matching on the last component
    if "/" in name:
        name = name.rsplit("/", maxsplit=1)[-1]
        return _normalize_skill_name(name, frontmatter_skills)

    # Try suffix match
    for fm_skill in frontmatter_skills:
        if fm_skill.endswith(f"-{name}"):
            return fm_skill

    return with_prefix


def _skill_path(skill_name: str) -> str:
    """Build the full installed path for a skill."""
    return f"{SKILLS_BASE}/{skill_name}/SKILL.md"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def build_reinforced_section(
    frontmatter_skills: list[str],
    table_rows: list[SkillTableRow],
) -> ReinforcedSection:
    """Build the reinforced section from frontmatter skills and table rows.

    Rules:
    - Skills with ``Always`` trigger -> phase sub-sections
    - Skills with conditional triggers -> on-demand table
    - If no table exists, ALL skills go in Phase 1
    """
    if not table_rows:
        # No table: all skills in a single phase
        return ReinforcedSection(
            phases=[PhaseGroup(phase_name="Startup", skills=list(frontmatter_skills))],
            on_demand=[],
            all_skills=list(frontmatter_skills),
        )

    phases: list[PhaseGroup] = []
    on_demand: list[OnDemandEntry] = []
    placed_skills: set[str] = set()

    # Group always-load rows by phase, deduplicating skills
    for row in table_rows:
        normalized = [
            _normalize_skill_name(s, frontmatter_skills) for s in row.skill_names
        ]
        # Skip skills already placed (handles "Already loaded" rows)
        new_skills = [s for s in normalized if s not in placed_skills]
        if not new_skills:
            continue

        if row.is_always:
            # Check if we already have this phase
            existing = None
            for pg in phases:
                if pg.phase_name == row.phase:
                    existing = pg
                    break
            if existing:
                existing.skills.extend(new_skills)
            else:
                phases.append(PhaseGroup(phase_name=row.phase, skills=list(new_skills)))
            placed_skills.update(new_skills)
        else:
            for skill in new_skills:
                trigger = row.trigger
                on_demand.append(OnDemandEntry(skill_name=skill, trigger=trigger))
            placed_skills.update(new_skills)

    # Any frontmatter skills not placed go into on-demand as "Load when needed"
    for skill in frontmatter_skills:
        if skill not in placed_skills:
            on_demand.append(
                OnDemandEntry(skill_name=skill, trigger="Load when needed")
            )

    all_skills = list(frontmatter_skills)
    return ReinforcedSection(phases=phases, on_demand=on_demand, all_skills=all_skills)


def render_reinforced_section(section: ReinforcedSection) -> str:
    """Render the reinforced section to markdown text."""
    lines = list(PREAMBLE_LINES)

    # Phase sub-sections
    for i, phase in enumerate(section.phases, 1):
        lines.append("")
        lines.append(f"### Phase {i}: {phase.phase_name}")
        lines.append("")
        lines.append("Read these files NOW:")
        for skill in phase.skills:
            lines.append(f"- `{_skill_path(skill)}`")

    # On-demand table
    if section.on_demand:
        lines.append("")
        lines.append("### On-Demand (load only when triggered)")
        lines.append("")
        lines.append("| Skill | Trigger |")
        lines.append("|-------|---------|")
        for entry in section.on_demand:
            lines.append(f"| `{_skill_path(entry.skill_name)}` | {entry.trigger} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section replacement
# ---------------------------------------------------------------------------
_SKILL_LOADING_HEADER_RE = re.compile(r"^##\s+Skill\s+Loading\b", re.IGNORECASE)
_NEXT_H2_RE = re.compile(r"^##\s+(?!#)", re.IGNORECASE)


def find_skill_loading_section(content: str) -> tuple[int, int] | None:
    """Find the line range of the Skill Loading section(s).

    Returns ``(start_line_idx, end_line_idx)`` where end is exclusive.
    The range covers from the first ``## Skill Loading`` header through
    any ``## Skill Loading Strategy`` section that immediately follows,
    up to (but not including) the next ``##`` header.

    Returns None if not found.
    """
    lines = content.splitlines()
    start = None
    end = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if start is None:
            if _SKILL_LOADING_HEADER_RE.match(stripped):
                start = i
        # We are inside the section. Look for the next ## that is NOT
        # another "Skill Loading" variant (some agents have both
        # "## Skill Loading -- MANDATORY" and "## Skill Loading Strategy")
        elif _NEXT_H2_RE.match(stripped) and not _SKILL_LOADING_HEADER_RE.match(
            stripped
        ):
            end = i
            break

    if start is None:
        return None

    # If we never found a next ##, section extends to end of file
    if end is None:
        end = len(lines)

    return start, end


def replace_skill_loading_section(content: str, new_section: str) -> str:
    """Replace the Skill Loading section in content with new_section."""
    bounds = find_skill_loading_section(content)
    if bounds is None:
        raise ValueError("No ## Skill Loading section found in content")

    start, end = bounds
    lines = content.splitlines()

    # Preserve trailing newline behavior
    had_trailing = content.endswith("\n")

    new_lines = new_section.splitlines()

    # Ensure a blank line separator between the new section and the next
    # section header (if there is content after the replaced section).
    if end < len(lines) and new_lines and new_lines[-1] != "":
        new_lines.append("")

    result_lines = lines[:start] + new_lines + lines[end:]
    result = "\n".join(result_lines)
    if had_trailing and not result.endswith("\n"):
        result += "\n"
    return result


# ---------------------------------------------------------------------------
# Load: directive updates in workflow phases
# ---------------------------------------------------------------------------
_LOAD_DIRECTIVE_RE = re.compile(r"^(Load:\s*)(.+?)(\s*(?:--|--).*)?$")


def update_load_directives(
    content: str,
    frontmatter_skills: list[str],
    *,
    apply_redundancy: bool,
) -> str:
    """Update ``Load:`` directives in workflow phases to use full paths.

    Only applies if ``apply_redundancy`` is True (for agents with 5+ skills).
    """
    if not apply_redundancy:
        return content

    lines = content.splitlines()
    result = []

    for line in lines:
        stripped = line.strip()
        m = _LOAD_DIRECTIVE_RE.match(stripped)
        if m:
            prefix = m.group(1)
            skills_part = m.group(2)
            suffix = m.group(3) or ""

            # Parse skill names from the directive
            raw_names = _parse_skill_names(skills_part)
            full_paths = []
            for name in raw_names:
                normalized = _normalize_skill_name(name, frontmatter_skills)
                full_paths.append(f"`{_skill_path(normalized)}`")

            new_skills = ", ".join(full_paths)
            # Preserve original indentation
            indent = line[: len(line) - len(line.lstrip())]
            result.append(f"{indent}{prefix}{new_skills}{suffix}")
        else:
            result.append(line)

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_section(
    agent_name: str,
    rendered: str,
    frontmatter_skills: list[str],
    original_line_count: int,
    skills_dir: Path = SKILLS_DIR,
) -> ValidationResult:
    """Validate a generated reinforced section."""
    result = ValidationResult(agent_name=agent_name)

    # 1. Every frontmatter skill appears exactly once
    for skill in frontmatter_skills:
        path = _skill_path(skill)
        count = rendered.count(path)
        if count == 0:
            result.errors.append(f"Skill '{skill}' not found in generated section")
        elif count > 1:
            result.errors.append(
                f"Skill '{skill}' appears {count} times (expected exactly 1)"
            )

    # 2. Every path resolves to actual directory
    for skill in frontmatter_skills:
        skill_dir = skills_dir / skill
        if not skill_dir.is_dir():
            result.warnings.append(f"Skill directory not found: {skill_dir}")

    # 3. No template variables remain in path-bearing lines
    #    (preamble legitimately contains {skill-name} as output instruction)
    preamble_len = len(PREAMBLE_LINES)
    non_preamble = "\n".join(rendered.splitlines()[preamble_len:])
    template_vars = ["{skill-name}", "{agent-name}", "{skill}"]
    for var in template_vars:
        if var in non_preamble:
            result.errors.append(
                f"Template variable '{var}' found in generated section"
            )

    # 4. Line count within budget
    new_count = len(rendered.splitlines())
    delta = new_count - original_line_count
    if delta > 20:
        result.warnings.append(f"Section grew by {delta} lines (budget: +5 to +16)")

    return result


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------
@dataclass
class ProcessResult:
    """Result of processing a single agent file."""

    agent_name: str
    original_content: str
    new_content: str
    validation: ValidationResult
    changed: bool

    @property
    def ok(self) -> bool:
        return self.validation.ok


def process_agent(path: Path, skills_dir: Path = SKILLS_DIR) -> ProcessResult:
    """Process a single agent file."""
    content = path.read_text(encoding="utf-8")
    agent_name = path.stem

    # Extract frontmatter skills
    fm_skills = extract_frontmatter_skills(content)
    if not fm_skills:
        return ProcessResult(
            agent_name=agent_name,
            original_content=content,
            new_content=content,
            validation=ValidationResult(
                agent_name=agent_name,
                warnings=["No skills in frontmatter -- skipping"],
            ),
            changed=False,
        )

    # Find existing section bounds for line count
    bounds = find_skill_loading_section(content)
    if bounds is None:
        return ProcessResult(
            agent_name=agent_name,
            original_content=content,
            new_content=content,
            validation=ValidationResult(
                agent_name=agent_name,
                errors=["No ## Skill Loading section found"],
            ),
            changed=False,
        )

    original_line_count = bounds[1] - bounds[0]

    # Parse existing table
    table_rows = parse_skill_table(content)

    # Build and render new section
    section = build_reinforced_section(fm_skills, table_rows)
    rendered = render_reinforced_section(section)

    # Replace section
    new_content = replace_skill_loading_section(content, rendered)

    # Update Load: directives for agents with 5+ skills
    apply_redundancy = len(fm_skills) >= 5
    new_content = update_load_directives(
        new_content, fm_skills, apply_redundancy=apply_redundancy
    )

    # Validate
    validation = validate_section(
        agent_name, rendered, fm_skills, original_line_count, skills_dir
    )

    return ProcessResult(
        agent_name=agent_name,
        original_content=content,
        new_content=new_content,
        validation=validation,
        changed=content != new_content,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Reinforce skill loading sections in agent definitions"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to agent files (default: dry-run)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        help="Process only this agent (e.g. nw-researcher)",
    )
    args = parser.parse_args(argv)

    # Determine which agents to process
    if args.agent:
        agent_file = AGENTS_DIR / f"{args.agent}.md"
        if not agent_file.exists():
            print(f"ERROR: Agent file not found: {agent_file}")
            return 1
        agent_files = [agent_file]
    else:
        agent_files = sorted(AGENTS_DIR.glob("nw-*.md"))

    if not agent_files:
        print("No agent files found")
        return 1

    results: list[ProcessResult] = []
    for agent_file in agent_files:
        result = process_agent(agent_file)
        results.append(result)

        # Display result
        status = "CHANGED" if result.changed else "UNCHANGED"
        icon = "*" if result.changed else " "
        print(f"[{icon}] {result.agent_name}: {status}")

        for err in result.validation.errors:
            print(f"    ERROR: {err}")
        for warn in result.validation.warnings:
            print(f"    WARN:  {warn}")

    # Apply if requested
    if args.apply:
        applied = 0
        for result in results:
            if result.changed and result.ok:
                agent_file = AGENTS_DIR / f"{result.agent_name}.md"
                agent_file.write_text(result.new_content, encoding="utf-8")
                applied += 1
                print(f"  APPLIED: {result.agent_name}")
            elif result.changed and not result.ok:
                print(f"  SKIPPED (errors): {result.agent_name}")
        print(f"\nApplied {applied} of {len(results)} agents")
    else:
        changed = sum(1 for r in results if r.changed)
        print(f"\nDry-run: {changed} of {len(results)} agents would change")
        if changed:
            print("Run with --apply to write changes")

    # Return non-zero if any validation errors
    has_errors = any(not r.ok for r in results if r.changed)
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
