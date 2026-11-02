"""Platform contract schemas -- single source of truth for cross-platform rules.

Defines canonical path rewrite mappings, forbidden fields, and exceptions
used by all installer plugins. Every plugin that handles platform differences
MUST import from this module rather than hardcoding rules locally (ADR-003).

Supported platforms: claude_code, opencode, codex, omp, devin.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import accumulate, pairwise


@dataclass(frozen=True)
class ToolEntry:
    name: str
    scope: str | None


ToolsLine = tuple[ToolEntry, ...]


@dataclass(frozen=True)
class UnbalancedToolSpecifier:
    raw: str


REPLY_CHANNEL_TOOLS = frozenset({"StructuredOutput"})
CLAUDE_INERT_TOOLS = (ToolEntry("TodoWrite", None), ToolEntry("TaskCreate", None))


def parse_tools_line(raw: str) -> ToolsLine | UnbalancedToolSpecifier:
    content = raw.strip()
    if content.startswith("[") and content.endswith("]"):
        content = content[1:-1]
    depths = tuple(accumulate(int(c == "(") - int(c == ")") for c in content))
    if any(depth < 0 for depth in depths) or (depths and depths[-1] != 0):
        return UnbalancedToolSpecifier(raw)
    boundaries = (
        -1,
        *(
            i
            for i, (char, depth) in enumerate(zip(content, depths, strict=True))
            if char == "," and depth == 0
        ),
        len(content),
    )
    entries = tuple(
        content[start + 1 : end].strip()
        for start, end in pairwise(boundaries)
        if content[start + 1 : end].strip()
    )
    return tuple(
        ToolEntry(entry.partition("(")[0].strip(), entry.partition("(")[2][:-1])
        if "(" in entry
        else ToolEntry(entry, None)
        for entry in entries
    )


def render_tools_line(line: ToolsLine) -> str:
    return ", ".join(
        entry.name if entry.scope is None else f"{entry.name}({entry.scope})"
        for entry in line
    )


def project_claude_tools(declared: ToolsLine) -> ToolsLine:
    kept = tuple(entry for entry in declared if entry.name not in REPLY_CHANNEL_TOOLS)
    return kept or CLAUDE_INERT_TOOLS


def project_claude_role_text(text: str) -> str | UnbalancedToolSpecifier:
    frontmatter = re.match(r"\A---\r?\n(.*?)(?=^---(?:\r?\n|$))", text, re.S | re.M)
    if frontmatter is None:
        return text
    tools = re.search(r"^tools:[ \t]*([^\r\n]*)", frontmatter[1], re.M)
    if tools is None:
        return text
    parsed = parse_tools_line(tools[1])
    if isinstance(parsed, UnbalancedToolSpecifier):
        return parsed
    start = frontmatter.start(1) + tools.start(1)
    end = frontmatter.start(1) + tools.end(1)
    return text[:start] + render_tools_line(project_claude_tools(parsed)) + text[end:]


def nwdes_cli_role_tools(role_id: str) -> tuple[str, ...]:
    """Supply the CLI recording capability for product and examiner roles."""
    if role_id == "nw-product-owner":
        return ("Read", "Write", "Bash", "SendMessage")
    return ("Read", "Bash") if role_id == "nw-user-examiner" else ()


def project_nwdes_role_text(text: str) -> str:
    """Replace reply-channel grants with the role's CLI recording tools."""
    import re

    frontmatter = re.match(r"\A---\r?\n(.*?)(?=^---(?:\r?\n|$))", text, re.S | re.M)
    if frontmatter is None:
        return text
    name = re.search(r"^name:[ \t]*([^\r\n]+)", frontmatter[1], re.M)
    if name is None:
        return text
    role_id = name[1].strip().strip("'\"")
    tools = nwdes_cli_role_tools(role_id)
    if not tools:
        return text
    projected = re.sub(
        r"^tools:[^\r\n]*(?:\r?\n[ \t]+-[^\r\n]*)*",
        lambda _: "tools: " + ", ".join(tools),
        frontmatter[1],
        flags=re.M,
    )
    if projected == frontmatter[1] and not re.search(r"^tools:", projected, re.M):
        projected += "tools: " + ", ".join(tools) + "\n"
    return text[: frontmatter.start(1)] + projected + text[frontmatter.end(1) :]


# -- Path Rewrite Rules (Claude Code -> OpenCode) ----------------------------
#
# Each entry maps a Claude Code path prefix to its OpenCode equivalent.
# Rules are applied in order; first match wins.
# More specific prefixes MUST appear before more general ones.

OPENCODE_PATH_REWRITES: tuple[tuple[str, str], ...] = (
    ("~/.claude/skills/", "~/.config/opencode/skills/"),
    ("~/.claude/agents/", "~/.config/opencode/agents/"),
    ("~/.claude/nWave/skills/", "~/.config/opencode/skills/"),
    ("~/.claude/nWave/", "~/.config/opencode/"),
)


# -- Path Rewrite Exceptions -------------------------------------------------
#
# Paths matching any of these prefixes are NEVER rewritten, even if they
# match a rewrite rule. The DES library path is the canonical example:
# it lives under ~/.claude/lib/python and must remain there.

OPENCODE_PATH_REWRITE_EXCEPTIONS: tuple[str, ...] = ("~/.claude/lib/python",)


# -- Skill Forbidden Fields (Claude Code only) -------------------------------
#
# YAML frontmatter fields that exist only in Claude Code's skill format.
# OpenCode does not recognize these fields; including them causes warnings
# or undefined behavior. The skills plugin MUST strip these during install.

OPENCODE_SKILL_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "user-invocable",
        "disable-model-invocation",
    }
)


# -- Command Forbidden Fields (Claude Code only) ------------------------------
#
# YAML frontmatter fields that exist only in Claude Code's command format.
# OpenCode does not recognize these fields; the commands plugin MUST strip
# them during install.

OPENCODE_COMMAND_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "argument-hint",
        "disable-model-invocation",
    }
)


# -- Codex CLI Path Rewrite Rules (Claude Code -> Codex CLI) -----------------
#
# Codex CLI skills live under $HOME/.agents/skills/ (NOT ~/.codex/).
# Agents live under ~/.codex/agents/ and hooks are wired via ~/.codex/hooks.json
# or the [hooks] section of ~/.codex/config.toml.

CODEX_PATH_REWRITES: tuple[tuple[str, str], ...] = (
    ("~/.claude/skills/", "~/.agents/skills/"),
    ("~/.claude/agents/", "~/.codex/agents/"),
    ("~/.claude/hooks/", "~/.codex/hooks/"),
    ("~/.claude/nWave/skills/", "~/.agents/skills/"),
    ("~/.claude/nWave/", "~/.codex/"),
)


# -- Codex CLI Skill Forbidden Fields ----------------------------------------
#
# Claude Code-only YAML frontmatter fields not recognised by Codex CLI.
# The codex_skills_plugin MUST strip these when copying SKILL.md files.

CODEX_SKILL_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "user-invocable",
        "disable-model-invocation",
    }
)


# -- Codex CLI Agent Forbidden Fields ----------------------------------------
#
# Claude Code agent frontmatter fields that have no TOML equivalent in Codex
# or that are handled separately by codex_agents_plugin.
#
# NOT forbidden (Codex TOML uses them directly):
#   name        -- required TOML field
#   description -- required TOML field
#   model       -- optional TOML field
#
# Forbidden (no Codex equivalent or handled by transform logic):
#   tools               -- Codex uses sandbox_mode/approval_policy at config level
#   skills              -- injected via $HOME/.agents/skills/, not per-agent TOML
#   maxTurns            -- no per-agent turn limit in Codex TOML schema
#   disable-model-invocation -- Claude Code-only field
#   permissionMode       -- Claude Code-only field
#   effort               -- Claude Code-only field; Codex 0.149.0 rejects the
#                           whole role file on any unknown field and drops the
#                           agent from the registry silently

CODEX_AGENT_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "tools",
        "skills",
        "maxTurns",
        "disable-model-invocation",
        "permissionMode",
        "effort",
    }
)


# -- OMP Path Rewrite Rules (Claude Code -> OMP) ------------------------------
#
# OMP discovers native skills at <config-root>/agent/skills/<name>/SKILL.md
# and native task agents at <config-root>/agent/agents/*.md, where the config
# root is $HOME/<PI_CONFIG_DIR or ".omp">. Rules are applied in order; first
# match wins; more specific prefixes MUST appear before more general ones.

OMP_PATH_REWRITES: tuple[tuple[str, str], ...] = (
    ("~/.claude/skills/", "~/.omp/agent/skills/"),
    ("~/.claude/agents/nw/", "~/.omp/agent/agents/"),
    ("~/.claude/agents/", "~/.omp/agent/agents/"),
    ("~/.claude/nWave/skills/", "~/.omp/agent/skills/"),
    ("~/.claude/nWave/", "~/.omp/agent/"),
)


# -- OMP Path Rewrite Exceptions ----------------------------------------------
#
# Same rule as OpenCode: the DES runtime lives under ~/.claude/lib/python and
# is reached through the host-neutral runtime pointer, never through a
# per-host skills/agents path. Rewriting it would point role bodies at a
# directory the runtime scheme does not publish.

OMP_PATH_REWRITE_EXCEPTIONS: tuple[str, ...] = ("~/.claude/lib/python",)


# -- Path Rewrite Rules (Claude Code -> Devin CLI) ----------------------------
#
# Devin CLI discovers global skills at ~/.config/devin/skills/ (canonical user
# path documented in devin skills paths). Rules follow the same ordering
# convention as OMP: more specific prefixes before general ones.
# The DES runtime lib path is excepted: skills reference it through the
# host-neutral pointer scheme, never through a per-host copy.

DEVIN_PATH_REWRITES: tuple[tuple[str, str], ...] = (
    ("~/.claude/skills/", "~/.config/devin/skills/"),
    ("~/.claude/agents/nw/", "~/.config/devin/skills/"),
    ("~/.claude/agents/", "~/.config/devin/skills/"),
    ("~/.claude/nWave/skills/", "~/.config/devin/skills/"),
    ("~/.claude/nWave/", "~/.config/devin/"),
)

DEVIN_PATH_REWRITE_EXCEPTIONS: tuple[str, ...] = ("~/.claude/lib/python",)


# -- OMP Agent Frontmatter Contract -------------------------------------------
#
# OMP task agents are Markdown with YAML frontmatter parsed by
# parseAgentFields(): required non-empty string ``name`` and ``description``
# plus the body as the system prompt. Optional keys include ``tools`` (CSV or
# array, lowercased builtin names, ``yield`` auto-added), ``spawns``,
# ``model`` (prioritized selector list), ``output`` (opaque schema data),
# ``autoloadSkills`` (skill names injected before the first child prompt),
# ``thinking-level``, ``blocking``. Unknown frontmatter keys are tolerated by
# discovery, so the fields below are OMITTED by the projection rather than
# stripped defensively:
#
#   model    -- nWave roles declare Claude aliases (sonnet/haiku/opus/
#               claude-*). OMP would treat them as model selectors and route
#               spawned roles away from the user's configured model. Omitting
#               the key entirely falls through to the parent session's active
#               model, which is the intended GLM inheritance.
#   maxTurns -- no per-agent turn cap in the OMP agent schema; the limit is a
#               Claude-side runtime control with no honest equivalent.
#   skills   -- replaced by ``autoloadSkills`` naming only the PUBLIC skills
#               actually installed for OMP, so each skill is delivered once
#               through the native autoload path instead of being inlined.
#
# ``StructuredOutput`` is a reply-channel token (REPLY_CHANNEL_TOOLS), never
# an executable capability: it is excluded from ``tools`` and expressed as an
# ``output`` schema projected from the canonical model envelope.

OMP_AGENT_OMITTED_FIELDS: frozenset[str] = frozenset({"model", "maxTurns", "skills"})
