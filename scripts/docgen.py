#!/usr/bin/env python3
"""nwave-docgen: Deterministic documentation generator for nWave artifacts.

Pipeline: scan → extract → enrich → render → write

Scans nWave agents, commands, skills, and templates from YAML front-matter,
resolves cross-references, and renders navigable Markdown reference pages.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import TypedDict


class DocgenError(Exception):
    """Raised for any data integrity issue — malformed YAML, missing fields, broken refs."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class Agent(TypedDict):
    name: str
    description: str
    model: str
    tools: list[str]
    max_turns: int
    skills: list[str]
    source_path: str
    wave: str
    commands: list[str]


class Command(TypedDict):
    name: str
    description: str
    argument_hint: str
    agents: list[str]
    source_path: str


class Skill(TypedDict):
    name: str
    description: str
    agent_dir: str
    source_path: str


class Template(TypedDict):
    name: str
    type: str
    description: str
    version: str
    source_path: str


# ---------------------------------------------------------------------------
# YAML front-matter parser (no pyyaml dependency — front-matter is simple)
# ---------------------------------------------------------------------------
_FRONT_MATTER_RE = re.compile(r"\A---\n(.*?\n)---", re.DOTALL)


def parse_front_matter(path: Path) -> dict:
    """Extract YAML front-matter as a flat dict. Supports scalar and list values."""
    text = path.read_text(encoding="utf-8")
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        raise DocgenError(f"Missing YAML front-matter in {path}")
    result: dict = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        list_match = re.match(r"^\s+-\s+(.+)$", line)
        if list_match and current_key is not None:
            if current_list is None:
                current_list = []
                result[current_key] = current_list
            current_list.append(list_match.group(1).strip())
            continue
        kv_match = re.match(r"^(\w[\w-]*):\s*(.*?)$", line)
        if kv_match:
            current_key = kv_match.group(1)
            val = kv_match.group(2).strip().strip('"').strip("'")
            current_list = None
            if val:
                result[current_key] = val
            continue
    return result


def require_fields(data: dict, fields: list[str], path: Path) -> None:
    """Raise DocgenError if any required field is missing."""
    missing = [f for f in fields if f not in data]
    if missing:
        raise DocgenError(f"Missing required fields {missing} in {path}")


# ---------------------------------------------------------------------------
# Stage 1: Scan
# ---------------------------------------------------------------------------
def scan(root: Path) -> dict[str, list[Path]]:
    """Discover artifact files grouped by type."""
    nwave = root / "nWave"
    agents = sorted((nwave / "agents").glob("*.md"))
    commands = sorted((nwave / "tasks" / "nw").glob("*.md"))
    skills = sorted((nwave / "skills").rglob("*.md"))
    templates = sorted(
        p for p in (nwave / "templates").glob("*.yaml") if not p.name.startswith(".")
    )
    return {
        "agents": agents,
        "commands": commands,
        "skills": skills,
        "templates": templates,
    }


# ---------------------------------------------------------------------------
# Stage 2: Extract
# ---------------------------------------------------------------------------
def extract_agent(path: Path) -> Agent:
    fm = parse_front_matter(path)
    require_fields(fm, ["name", "description"], path)
    tools_raw = fm.get("tools", "")
    tools = (
        [t.strip() for t in tools_raw.split(",")]
        if isinstance(tools_raw, str)
        else tools_raw
    )
    skills = fm.get("skills", [])
    if isinstance(skills, str):
        skills = [skills]
    return Agent(
        name=fm["name"],
        description=fm["description"],
        model=fm.get("model", "inherit"),
        tools=tools,
        max_turns=int(fm.get("maxTurns", fm.get("max_turns", 0))),
        skills=skills,
        source_path=str(path),
    )


def extract_command(path: Path) -> Command:
    fm = parse_front_matter(path)
    require_fields(fm, ["description"], path)
    # Extract agent references from command body
    text = path.read_text(encoding="utf-8")
    agent_refs = sorted(set(re.findall(r"\bnw-[a-z]+-?[a-z]*(?:-[a-z]+)*", text)))
    return Command(
        name=path.stem,
        description=fm["description"].strip('"').strip("'"),
        argument_hint=fm.get("argument-hint", fm.get("argument_hint", "")),
        agents=agent_refs,
        source_path=str(path),
    )


def _infer_skill_from_content(path: Path) -> dict:
    """Infer name and description from H1 heading and first paragraph."""
    text = path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    name = path.stem
    description = ""
    for i, line in enumerate(lines):
        h1 = re.match(r"^#\s+(.+)$", line)
        if h1:
            name = h1.group(1).strip()
            # First non-empty line after heading is description
            for subsequent in lines[i + 1 :]:
                stripped = subsequent.strip()
                if (
                    stripped
                    and not stripped.startswith("#")
                    and not stripped.startswith("Cross-ref")
                ):
                    description = stripped
                    break
            break
    return {"name": path.stem, "description": description or name}


def extract_skill(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    if _FRONT_MATTER_RE.match(text):
        fm = parse_front_matter(path)
        require_fields(fm, ["name", "description"], path)
    else:
        fm = _infer_skill_from_content(path)
    return Skill(
        name=fm["name"],
        description=fm["description"],
        agent_dir=path.parent.name,
        source_path=str(path),
    )


def _parse_yaml_keys(path: Path) -> dict:
    """Parse top-level scalar keys from a YAML file (with or without front-matter)."""
    text = path.read_text(encoding="utf-8")
    m = _FRONT_MATTER_RE.match(text)
    content = m.group(1) if m else text
    result: dict = {}
    for line in content.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        kv = re.match(r"^(\w[\w_-]*):\s*[\"']?([^\"'\n]+?)[\"']?\s*$", line)
        if kv:
            result[kv.group(1)] = kv.group(2).strip()
    return result


def extract_template(path: Path) -> Template:
    fm = _parse_yaml_keys(path)
    desc = fm.get("description", fm.get("template_name", fm.get("Purpose", "")))
    if not desc:
        # Use first comment line as description
        for line in path.read_text(encoding="utf-8").splitlines():
            comment = re.match(r"^#\s*(.+)$", line)
            if comment and not comment.group(1).startswith("="):
                desc = comment.group(1).strip()
                break
    if not desc:
        raise DocgenError(f"Cannot determine description for template {path}")
    return Template(
        name=path.stem,
        type=fm.get("template_type", fm.get("type", "unknown")),
        description=desc,
        version=fm.get("version", fm.get("template_version", "")),
        source_path=str(path),
    )


def extract_all(paths: dict[str, list[Path]]) -> dict[str, list]:
    return {
        "agents": [extract_agent(p) for p in paths["agents"]],
        "commands": [extract_command(p) for p in paths["commands"]],
        "skills": [extract_skill(p) for p in paths["skills"]],
        "templates": [extract_template(p) for p in paths["templates"]],
    }


# ---------------------------------------------------------------------------
# Stage 3: Enrich (cross-references)
# ---------------------------------------------------------------------------
# Patterns to detect wave from agent descriptions.
# Uses "X wave" phrase matching to avoid substring false positives
# (e.g., "product discovery" should not match DISCOVER wave).
_WAVE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bDISCOVER(?:Y)?\s+wave\b", re.IGNORECASE), "DISCOVER"),
    (re.compile(r"\bDISCUSS\s+wave\b", re.IGNORECASE), "DISCUSS"),
    (re.compile(r"\bDISTILL\s+wave\b", re.IGNORECASE), "DISTILL"),
    (re.compile(r"\bDESIGN\s+wave\b", re.IGNORECASE), "DESIGN"),
    (re.compile(r"\bDELIVER\s+wave\b", re.IGNORECASE), "DELIVER"),
    (re.compile(r"\bDEVOP\s+wave\b", re.IGNORECASE), "DEVOP"),
]

_WAVE_ORDER = [
    "DISCOVER",
    "DISCUSS",
    "DESIGN",
    "DISTILL",
    "DELIVER",
    "DEVOP",
    "Other",
]


def _infer_wave(description: str) -> str:
    """Infer wave from agent description. Matches 'X wave' to avoid substring hits."""
    for pattern, wave in _WAVE_PATTERNS:
        if pattern.search(description):
            return wave
    return "Other"


def enrich(data: dict[str, list]) -> dict[str, list]:
    """Resolve cross-references and add derived fields."""
    # Build lookup: both "skill-name" and "agent-dir/skill-name" resolve
    skill_lookup: set[str] = set()
    for s in data["skills"]:
        skill_lookup.add(s["name"])
        skill_lookup.add(f"{s['agent_dir']}/{s['name']}")
    agent_names = {a["name"] for a in data["agents"]}
    agent_dirs = {a["name"].removeprefix("nw-") for a in data["agents"]}

    # Validate agent→skill refs
    for agent in data["agents"]:
        for skill_ref in agent["skills"]:
            if skill_ref not in skill_lookup:
                raise DocgenError(
                    f"Agent '{agent['name']}' references skill '{skill_ref}' which does not exist"
                )

    # Validate skill→agent refs (parent dir must match an agent)
    for skill in data["skills"]:
        if skill["agent_dir"] not in agent_dirs:
            raise DocgenError(
                f"Skill '{skill['name']}' in dir '{skill['agent_dir']}' has no matching agent"
            )

    # Enrich: infer wave for each agent
    for agent in data["agents"]:
        agent["wave"] = _infer_wave(agent["description"])

    # Enrich: reviewer agents inherit parent agent's wave
    agent_wave = {a["name"]: a["wave"] for a in data["agents"]}
    for agent in data["agents"]:
        if agent["wave"] == "Other" and agent["name"].endswith("-reviewer"):
            parent = agent["name"].removesuffix("-reviewer")
            if parent in agent_wave and agent_wave[parent] != "Other":
                agent["wave"] = agent_wave[parent]

    # Enrich: filter command agent refs to only valid agent names
    for cmd in data["commands"]:
        cmd["agents"] = [a for a in cmd["agents"] if a in agent_names]

    # Enrich: build agent→commands reverse mapping
    agent_commands: dict[str, list[str]] = {}
    for cmd in data["commands"]:
        for agent_name in cmd["agents"]:
            agent_commands.setdefault(agent_name, []).append(cmd["name"])
    for agent in data["agents"]:
        agent["commands"] = sorted(set(agent_commands.get(agent["name"], [])))

    return data


# ---------------------------------------------------------------------------
# Stage 4: Render
# ---------------------------------------------------------------------------
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _skills_for_agent(agent: Agent, skills: list[Skill]) -> list[Skill]:
    """Return skills referenced by an agent, matching both 'name' and 'dir/name' forms."""
    skill_refs = set(agent["skills"])
    result = []
    for s in skills:
        if s["name"] in skill_refs or f"{s['agent_dir']}/{s['name']}" in skill_refs:
            result.append(s)
    return result


def render_master_index(data: dict[str, list]) -> str:
    return "\n".join(
        [
            "# nWave Reference",
            "",
            f"Auto-generated documentation for {len(data['agents'])} agents, "
            f"{len(data['commands'])} commands, {len(data['skills'])} skills, "
            f"and {len(data['templates'])} templates.",
            "",
            "## Contents",
            "",
            f"- [Agents](agents/index.md) ({len(data['agents'])})",
            f"- [Commands](commands/index.md) ({len(data['commands'])})",
            f"- [Skills](skills/index.md) ({len(data['skills'])})",
            f"- [Templates](templates/index.md) ({len(data['templates'])})",
            "",
        ]
    )


def render_agents_index(agents: list[Agent], skills: list[Skill]) -> str:
    lines = ["# Agents", ""]
    # Group by wave
    by_wave: dict[str, list[Agent]] = {}
    for a in agents:
        by_wave.setdefault(a.get("wave", "Other"), []).append(a)
    for wave in _WAVE_ORDER:
        wave_agents = by_wave.get(wave, [])
        if not wave_agents:
            continue
        lines.append(f"## {wave}")
        lines.append("")
        rows = []
        for a in sorted(wave_agents, key=lambda x: x["name"]):
            agent_skills = _skills_for_agent(a, skills)
            link = f"[{a['name']}]({a['name']}.md)"
            rows.append([link, a["description"], str(len(agent_skills))])
        lines.append(_md_table(["Name", "Description", "Skills"], rows))
        lines.append("")
    # All Agents reference table
    lines.append("## All Agents")
    lines.append("")
    all_rows = []
    for a in sorted(agents, key=lambda x: x["name"]):
        agent_skills = _skills_for_agent(a, skills)
        link = f"[{a['name']}]({a['name']}.md)"
        wave = a.get("wave", "Other")
        all_rows.append([link, wave, a["description"], str(len(agent_skills))])
    lines.append(_md_table(["Name", "Wave", "Description", "Skills"], all_rows))
    lines.append("")
    return "\n".join(lines)


def render_agent_detail(agent: Agent, skills: list[Skill]) -> str:
    agent_skills = _skills_for_agent(agent, skills)
    wave = agent.get("wave", "Other")
    commands = agent.get("commands", [])
    lines = [
        f"# {agent['name']}",
        "",
        agent["description"],
        "",
        f"**Wave:** {wave}",
        f"**Model:** {agent['model']}",
        f"**Max turns:** {agent['max_turns']}",
        f"**Tools:** {', '.join(agent['tools'])}",
        "",
    ]
    if commands:
        lines.append("## Commands")
        lines.append("")
        for cmd_name in commands:
            lines.append(f"- [`/nw:{cmd_name}`](../commands/index.md)")
        lines.append("")
    if agent_skills:
        lines.append("## Skills")
        lines.append("")
        for s in sorted(agent_skills, key=lambda x: x["name"]):
            skill_path = f"../../../nWave/skills/{s['agent_dir']}/{s['name']}.md"
            lines.append(f"- [{s['name']}]({skill_path}) — {s['description']}")
        lines.append("")
    return "\n".join(lines)


def render_commands_index(commands: list[Command]) -> str:
    rows = []
    for c in sorted(commands, key=lambda x: x["name"]):
        agent_links = ", ".join(f"[{a}](../agents/{a}.md)" for a in c.get("agents", []))
        rows.append(
            [f"`/nw:{c['name']}`", c["description"], agent_links, c["argument_hint"]]
        )
    table = _md_table(["Command", "Description", "Agents", "Arguments"], rows)
    return f"# Commands\n\n{table}\n"


def render_skills_index(skills: list[Skill]) -> str:
    lines = ["# Skills", ""]
    by_agent: dict[str, list[Skill]] = {}
    for s in skills:
        by_agent.setdefault(s["agent_dir"], []).append(s)
    for agent_dir in sorted(by_agent):
        agent_link = f"[nw-{agent_dir}](../agents/nw-{agent_dir}.md)"
        lines.append(f"## {agent_link}")
        lines.append("")
        for s in sorted(by_agent[agent_dir], key=lambda x: x["name"]):
            skill_path = f"../../../nWave/skills/{s['agent_dir']}/{s['name']}.md"
            lines.append(f"- [{s['name']}]({skill_path}) — {s['description']}")
        lines.append("")
    return "\n".join(lines)


def render_templates_index(templates: list[Template]) -> str:
    rows = []
    for t in sorted(templates, key=lambda x: x["name"]):
        rows.append([t["name"], t["type"], t["description"]])
    table = _md_table(["Name", "Type", "Description"], rows)
    return f"# Templates\n\n{table}\n"


def render(data: dict[str, list]) -> dict[str, str]:
    """Render all pages. Returns {relative_path: content}."""
    pages: dict[str, str] = {}
    pages["index.md"] = render_master_index(data)
    pages["agents/index.md"] = render_agents_index(data["agents"], data["skills"])
    pages["commands/index.md"] = render_commands_index(data["commands"])
    pages["skills/index.md"] = render_skills_index(data["skills"])
    pages["templates/index.md"] = render_templates_index(data["templates"])

    for agent in data["agents"]:
        filename = f"agents/{agent['name']}.md"
        pages[filename] = render_agent_detail(agent, data["skills"])

    return pages


# ---------------------------------------------------------------------------
# Stage 5: Write
# ---------------------------------------------------------------------------
def write_pages(pages: dict[str, str], output_dir: Path) -> None:
    """Write pages to output_dir, cleaning it first for deterministic output."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    for rel_path, content in pages.items():
        full_path = output_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")


def check_pages(pages: dict[str, str], output_dir: Path) -> list[str]:
    """Return list of stale/missing files. Empty = up to date."""
    stale: list[str] = []
    for rel_path, content in pages.items():
        full_path = output_dir / rel_path
        if not full_path.exists():
            stale.append(f"missing: {rel_path}")
        elif full_path.read_text(encoding="utf-8") != content:
            stale.append(f"stale: {rel_path}")
    return stale


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(root: Path, output_dir: Path) -> dict[str, str]:
    """Execute full pipeline: scan → extract → enrich → render. Returns pages."""
    paths = scan(root)
    data = extract_all(paths)
    data = enrich(data)
    return render(data)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate nWave reference documentation"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: docs/reference/)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if generated docs are up to date (exit 1 if stale)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    output_dir = args.output_dir or root / "docs" / "reference"

    try:
        pages = run_pipeline(root, output_dir)
    except DocgenError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.check:
        stale = check_pages(pages, output_dir)
        if stale:
            print("Documentation is out of date:", file=sys.stderr)
            for s in stale:
                print(f"  {s}", file=sys.stderr)
            return 1
        print("Documentation is up to date.")
        return 0

    write_pages(pages, output_dir)
    print(f"Generated {len(pages)} pages in {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
