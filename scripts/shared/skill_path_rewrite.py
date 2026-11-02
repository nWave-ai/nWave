"""Per-host skill-path rewrite -- single source of truth for body path rewriting.

Installer plugins deploy agent and skill bodies into per-host directories. The
canonical Claude Code source body references ``~/.claude/skills/`` (and sibling
``~/.claude/...`` prefixes). For non-Claude hosts those tokens point at a dead
path and MUST be rewritten to the host's own base.

This module exposes one pure function, :func:`rewrite_host_paths`, consumed by
all four host plugins (codex-agents, codex-skills, opencode-skills,
opencode-agents). It re-uses the host->base mapping SSOT already defined in
``scripts.shared.platform_contracts`` -- no new path constants are introduced.

The exception-aware char-scan loop is the canonical algorithm extracted from
``opencode_commands_plugin._rewrite_paths``: rules are applied in order and each
match is checked against the host's exception prefixes before being rewritten.

The function is pure (no IO, no side effects) and idempotent -- applying it to
already-rewritten content is a fixpoint, since no ``~/.claude/...`` rule matches
a host base that has already been substituted.
"""

from __future__ import annotations

from scripts.shared.platform_contracts import (
    CODEX_PATH_REWRITES,
    DEVIN_PATH_REWRITE_EXCEPTIONS,
    DEVIN_PATH_REWRITES,
    OMP_PATH_REWRITE_EXCEPTIONS,
    OMP_PATH_REWRITES,
    OPENCODE_PATH_REWRITE_EXCEPTIONS,
    OPENCODE_PATH_REWRITES,
)


# -- Per-host rewrite rule + exception tables (keyed view of the SSOT) --------
#
# "claude_code" is the canonical no-op host: empty rules -> body returned
# verbatim, preserving the A06 validator anchor on ~/.claude/skills/.
# Codex has no exception tuple today (its rules target skills/agents/hooks/nWave,
# never lib/, so a lib/python token is left alone by absence-of-rule). OMP
# carries the same lib/python exception as OpenCode: role bodies must keep
# naming the DES runtime through its pointer scheme, never a per-host copy.

HOST_PATH_REWRITES: dict[str, tuple[tuple[str, str], ...]] = {
    "claude_code": (),
    "opencode": OPENCODE_PATH_REWRITES,
    "codex": CODEX_PATH_REWRITES,
    "omp": OMP_PATH_REWRITES,
    "devin": DEVIN_PATH_REWRITES,
}

HOST_PATH_REWRITE_EXCEPTIONS: dict[str, tuple[str, ...]] = {
    "claude_code": (),
    "opencode": OPENCODE_PATH_REWRITE_EXCEPTIONS,
    "codex": (),
    "omp": OMP_PATH_REWRITE_EXCEPTIONS,
    "devin": DEVIN_PATH_REWRITE_EXCEPTIONS,
}

_EXCEPTION_CONTEXT_WINDOW = 100


def _is_exception_path(text_segment: str, exceptions: tuple[str, ...]) -> bool:
    """Return True if the match begins an exception path.

    The segment starts exactly at a rewrite match. A match is protected only
    when it is the leading portion of an exception path -- i.e. the segment
    starts with that exception. A position-anchored ``startswith`` check (rather
    than a substring ``in`` check) is required: an unrelated exception token
    appearing LATER in the same window (e.g. ``~/.claude/lib/python`` on the
    next line after a ``~/.claude/skills/`` reference) must NOT shield the
    earlier, legitimately-rewritable match.

    Args:
        text_segment: Text starting at a rewrite match
        exceptions: Exception prefixes that must never be rewritten for the host

    Returns:
        True if the match is the start of an exception path
    """
    return any(text_segment.startswith(exception) for exception in exceptions)


def rewrite_host_paths(body: str, host: str) -> str:
    """Rewrite canonical Claude Code paths in ``body`` to the host's base.

    Pure function. For ``host="claude_code"`` (or any unknown host) the body is
    returned unchanged. Otherwise the host's rewrite rules are applied in order,
    each match guarded against the host's exception prefixes.

    Args:
        body: Body text containing canonical ``~/.claude/...`` path tokens
        host: Target host key ("claude_code", "opencode", "codex")

    Returns:
        Body text with all non-exception host paths rewritten; idempotent.
    """
    rules = HOST_PATH_REWRITES.get(host, ())
    exceptions = HOST_PATH_REWRITE_EXCEPTIONS.get(host, ())

    result = body
    for claude_prefix, host_prefix in rules:
        new_result: list[str] = []
        remaining = result
        while claude_prefix in remaining:
            match_index = remaining.index(claude_prefix)
            context_end = min(match_index + _EXCEPTION_CONTEXT_WINDOW, len(remaining))
            context_segment = remaining[match_index:context_end]
            if _is_exception_path(context_segment, exceptions):
                new_result.append(remaining[: match_index + len(claude_prefix)])
                remaining = remaining[match_index + len(claude_prefix) :]
            else:
                new_result.append(remaining[:match_index])
                new_result.append(host_prefix)
                remaining = remaining[match_index + len(claude_prefix) :]
        new_result.append(remaining)
        result = "".join(new_result)
    return result
