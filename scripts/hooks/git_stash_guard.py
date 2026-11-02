"""git-stash guard PreToolUse hook -- slice-01 of fix-crafter-stash-structural-mitigation.

A STANDALONE Claude Code PreToolUse/Bash hook that mechanically enforces the
STANDING "no git stash, use git worktree" rule (10 cumulative text-rule
violations as of 2026-05-28 -- see
[[feedback_no_worktrees_no_excessive_parallel_2026_05_19]]). The hook receives
the tool invocation event as JSON on stdin, inspects `tool_input.command`, and
dispatches:

  Fast-path (non-git-stash Bash):
    Regex-match `^\\s*git\\s+stash\\b` on the command. If NO match, exit 0
    silently -- a bare Python early-exit before any filesystem work. The
    HOOK_EVENTS registration greps the command before spawning the
    interpreter, and this Python entry point repeats the discriminator so the
    decision is unambiguous even when invoked directly.

  Mutating git-stash path (BLOCK):
    A mutating subcommand (bare `git stash`, or `push`/`pop`/`apply`/`drop`/
    `clear`/`save`/`branch`/`create`/`store`) is refused: print
    `{"decision": "block", "reason": "..."}` to stdout + exit 2. The reason
    names ordinary Git worktree isolation AND the
    bypass mechanism (`NWAVE_GIT_STASH_ALLOW`) so the operator sees an
    actionable remedy.

  Read-only git-stash path (ALLOW):
    `git stash list`, `git stash show` (incl. `-p`), and any `git stash`
    carrying `--help`/`-h` are read-only/help forms -- exit 0 silently.

  Kill-switch (ALLOW + audit):
    When the command IS a mutating `git stash` AND `NWAVE_GIT_STASH_ALLOW` is
    set to a truthy value (any non-empty string that is not `0`/`false`/`no`/
    `off`, case-insensitive),
    the hook APPROVES (exit 0) and emits one audited `GitStashBypassUsed`
    event (JSONL) to `<target>/.nwave/des/logs/audit-{today}.log`. The event
    carries the `command` field so the operator sees which stash invocation
    was deliberately allowed.

Substrate (Ale 2026-05-28 framing): Claude Code hook lifecycle. NOT git. The
pre-commit framework's INTERNAL `git stash` ("Stashing unstaged files") is a
subprocess spawned BY the pre-commit binary, NOT a Claude `Bash` tool
invocation, so it is never intercepted by this PreToolUse hook.

Stdlib-only (no PyYAML, no third-party deps). Uses the standard PreToolUse/Bash
protocol: JSON stdin, block decision, and audited kill-switch bypasses.

Hook protocol contract (Claude Code PreToolUse on Bash):
    stdin = {"tool_name": "Bash", "tool_input": {"command": "...", ...}, ...}
    stdout (block) = {"decision": "block", "reason": "..."}
    stdout (approve) = "" (empty; exit code 0 is the signal)
    exit 0 = allow tool invocation
    exit 2 = block tool invocation (with stdout JSON for reason)

Test-harness env-var contract (slice-01 ATs):
    NWAVE_GIT_STASH_ALLOW -- kill-switch; truthy value bypasses the block
        (audited GitStashBypassUsed event).
    NWAVE_GIT_STASH_GUARD_TARGET_ROOT -- target machine root override so the
        hook locates the audit-log dir without relying on Path.cwd().

In production (no target-root override), the hook uses `Path.cwd()` as the
target root and `<target>/.nwave/des/logs/` as the audit-log dir.
"""

from __future__ import annotations

import json
import sys


# Decision algorithm lives in `nwave_ai.hooks.stash`
# (fix-execution-log-bash-guard-consolidation follow-on, Ale-authorised) --
# this script is now a thin stdin/stdout/exit-code CLI wrapper around it, so
# the universal nwave_ai.hooks PreToolUse/Bash handler and this standalone
# registration cannot diverge into two decision algorithms. Imported lazily
# inside `main()` so the module still parses even when `nwave_ai` is not on
# `sys.path` (bootstrap-self exemption, matching the sibling worktree guard).
def _guards():
    from nwave_ai.hooks import stash as bash_command_guards

    return bash_command_guards


def _read_hook_event() -> dict[str, object]:
    """Read the Claude Code PreToolUse hook event JSON from stdin.

    Returns `{}` if stdin is empty or malformed; the caller treats this as a
    non-actionable event (approve silently). The hook fails OPEN on protocol
    violations -- a malformed event is a Claude Code bug, not an operator
    violation.
    """
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _bash_command(event: dict[str, object]) -> str:
    """Extract the bash command literal from the hook event payload."""
    tool_input = event.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command", "")
    return command if isinstance(command, str) else ""


def _session_id(event: dict[str, object]) -> str:
    """Extract the Claude Code session id from the hook event payload."""
    session_id = event.get("session_id", "")
    return session_id if isinstance(session_id, str) else ""


def main() -> int:
    """Read the hook event, delegate the decision, return the exit code.

    All decision logic (fast-path, read-only vs mutating, kill-switch) lives
    in `bash_command_guards.evaluate_git_stash_command`; this wrapper only
    translates the stdin event into that call and the returned decision into
    the stdout/exit-code protocol.
    """
    guards = _guards()
    event = _read_hook_event()
    command = _bash_command(event)
    decision = guards.evaluate_git_stash_command(command)
    if decision is None:
        return 0
    if decision.audit_event is not None:
        guards.write_bash_guard_audit_event(
            guards.git_stash_guard_target_root(),
            decision.audit_event,
            {**(decision.audit_data or {}), "session_id": _session_id(event)},
        )
    if decision.allow:
        return 0
    print(json.dumps({"decision": "block", "reason": decision.reason}, sort_keys=True))
    return 2


if __name__ == "__main__":
    sys.exit(main())
