"""Platform contract schemas -- single source of truth for cross-platform rules.

Defines canonical path rewrite mappings, forbidden fields, and exceptions
used by all installer plugins. Every plugin that handles platform differences
MUST import from this module rather than hardcoding rules locally (ADR-003).

Supported platforms: claude_code, opencode, codex.
"""

from __future__ import annotations


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

CODEX_AGENT_FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "tools",
        "skills",
        "maxTurns",
        "disable-model-invocation",
    }
)
