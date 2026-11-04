"""Shared Bash PreToolUse decision authority for guarded git operations.

Moved verbatim from the removed DES runtime (S5-OQ6 closure, F212): the git-stash
guard predicates once in the retired ``bash_command_guards`` module plus
the envelope-parsing wrapper ``evaluate_bash_safety_guards`` once in the DES
pre-tool-use handler. Single algorithm for the decisions formerly duplicated
across the standalone ``scripts/hooks/git_stash_guard.py`` PreToolUse/Bash hook
registration (which the kept hook set repoints here). Both the standalone script
and the universal PreToolUse/Bash handler call the SAME function here.

Fast-path contract: the evaluator returns ``None`` immediately when its git
shape is absent.
"""

from __future__ import annotations

import json
import os
import re
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nwave_ai.platform.project_root import anchor_to_project_root


@dataclass(frozen=True)
class BashGuardDecision:
    """The outcome of one Bash guard evaluation.

    ``allow=False`` carries the human-readable block reason. An allow that
    happened via an audited override carries ``audit_event``/``audit_data``;
    the caller is responsible for actually writing the audit record (kept
    outside this pure decision function so it stays synchronously testable).
    """

    allow: bool
    reason: str | None = None
    audit_event: str | None = None
    audit_data: dict[str, object] | None = None


_AUDIT_LOG_DIR_RELPATH = Path(".nwave") / "des" / "logs"


def _split_subcommands(command: str) -> list[list[str]] | None:
    """Tokenize shell command groups for the independent host-scan guard."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    separators = frozenset({"&&", "||", ";", "|", "&"})
    sub_commands: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in separators:
            if current:
                sub_commands.append(current)
                current = []
        else:
            current.append(token)
    if current:
        sub_commands.append(current)
    return sub_commands


def _audit_log_path(target_root: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return target_root / _AUDIT_LOG_DIR_RELPATH / f"audit-{today}.log"


def write_bash_guard_audit_event(
    target_root: Path, event: str, data: dict[str, object]
) -> None:
    """Append one audit event to today's JSONL audit log under ``target_root``."""
    log_path = _audit_log_path(target_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
# git stash
# --------------------------------------------------------------------------

_GIT_STASH_ALLOW_ENV = "NWAVE_GIT_STASH_ALLOW"
_GIT_STASH_GUARD_TARGET_ROOT_ENV = "NWAVE_GIT_STASH_GUARD_TARGET_ROOT"
_GIT_STASH_RE = re.compile(r"^\s*git\s+stash\b")
_STASH_READ_ONLY_SUBCOMMANDS = frozenset({"list", "show"})
_STASH_HELP_FLAGS = frozenset({"--help", "-h"})
_FALSY_ENV_VALUES = frozenset({"0", "false", "no", "off"})

_STASH_BLOCK_REASON = (
    "git stash is forbidden per STANDING (10 cumulative violations); "
    "use an ordinary Git worktree for clean-tree isolation instead. "
    "To bypass deliberately, set NWAVE_GIT_STASH_ALLOW=1 "
    "(audited GitStashBypassUsed event)."
)

STASH_BYPASS_EVENT = "GitStashBypassUsed"


def is_git_stash_command(command: str) -> bool:
    """True iff ``command`` begins with ``git stash`` (word-boundary match)."""
    return _GIT_STASH_RE.match(command) is not None


def _first_subcommand_after_stash(tokens: list[str]) -> str | None:
    seen_stash = False
    for token in tokens:
        if not seen_stash:
            if token == "stash":
                seen_stash = True
            continue
        if token.startswith("-"):
            continue
        return token
    return None


def is_mutating_git_stash_command(command: str) -> bool:
    """True iff a ``git stash`` command mutates state (block candidate).

    Read-only forms: ``list``, ``show`` (any flags), and any invocation carrying
    ``--help``/``-h``. Everything else -- including bare ``git stash`` -- mutates.
    """
    tokens = command.split()
    if any(token in _STASH_HELP_FLAGS for token in tokens):
        return False
    subcommand = _first_subcommand_after_stash(tokens)
    return subcommand not in _STASH_READ_ONLY_SUBCOMMANDS


def git_stash_allow_env_active() -> bool:
    """True when ``NWAVE_GIT_STASH_ALLOW`` carries a truthy value."""
    raw = os.environ.get(_GIT_STASH_ALLOW_ENV, "")
    if not raw:
        return False
    return raw.strip().lower() not in _FALSY_ENV_VALUES


def git_stash_guard_target_root() -> Path:
    override = os.environ.get(_GIT_STASH_GUARD_TARGET_ROOT_ENV, "")
    return Path(override) if override else anchor_to_project_root(Path.cwd())


def evaluate_git_stash_command(command: str) -> BashGuardDecision | None:
    """Decide a Bash command against the git-stash guard's rule.

    Returns ``None`` on the fast path (not a ``git stash`` invocation at all)
    -- no further work is owed. Returns an allow decision for read-only
    forms and for a validly-overridden mutating form (carrying the audit
    event the caller must write), and a block decision otherwise.
    """
    if not is_git_stash_command(command):
        return None
    if not is_mutating_git_stash_command(command):
        return BashGuardDecision(allow=True)
    if git_stash_allow_env_active():
        return BashGuardDecision(
            allow=True,
            audit_event=STASH_BYPASS_EVENT,
            audit_data={"command": command},
        )
    return BashGuardDecision(allow=False, reason=_STASH_BLOCK_REASON)


def evaluate_bash_safety_guards(
    hook_input: dict[str, object], tool_input: dict[str, object]
) -> dict[str, str] | None:
    """The git-stash Bash guard decision, parsed from one hook envelope.

    The single decision authority is :func:`evaluate_git_stash_command`; this
    function is one envelope-parsing wrapper around it. The standalone script
    (``scripts/hooks/git_stash_guard.py``, repointed here) calls the shared
    predicate authority directly (its own CLI envelope shape), NOT necessarily
    this helper. ``nwave_ai.hooks.__main__.main`` calls THIS helper by name,
    once, BEFORE the activation gate (ADR-AG-001 ordering repair), so an
    inactive project cannot exit 0 past a live stash mutation. Returns a
    ``{decision: block, reason: ...}`` payload, or ``None`` to allow (paying no
    audit/filesystem work when the guard's command shape did not match).
    """
    command = tool_input.get("command")
    if not isinstance(command, str) or not command:
        return None

    stash_decision = evaluate_git_stash_command(command)
    if stash_decision is not None:
        if stash_decision.audit_event is not None:
            write_bash_guard_audit_event(
                git_stash_guard_target_root(),
                stash_decision.audit_event,
                {
                    **(stash_decision.audit_data or {}),
                    "session_id": str(hook_input.get("session_id", "")),
                },
            )
        if not stash_decision.allow:
            return {"decision": "block", "reason": stash_decision.reason or ""}
        return None

    return None


__all__ = [
    "STASH_BYPASS_EVENT",
    "BashGuardDecision",
    "evaluate_bash_safety_guards",
    "evaluate_git_stash_command",
    "git_stash_allow_env_active",
    "git_stash_guard_target_root",
    "is_git_stash_command",
    "is_mutating_git_stash_command",
    "write_bash_guard_audit_event",
]
