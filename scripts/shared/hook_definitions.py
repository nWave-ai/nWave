"""Canonical DES hook definitions -- single source of truth.

Both the plugin builder (build_plugin.py) and the custom installer
(des_plugin.py) generate Claude Code hook configurations. This module
provides the shared definitions so hook events, matchers, and actions
are defined exactly once.

The two distribution paths differ only in HOW the Python command is
constructed (plugin uses CLAUDE_PLUGIN_ROOT, installer uses $HOME),
not in WHAT hooks are registered.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookEvent:
    """A single DES hook event registration.

    Attributes:
        event: Claude Code hook event type (e.g., "PreToolUse").
        matcher: Optional matcher string (e.g., "Agent", "Write").
            None means the hook fires for all invocations of that event.
        action: DES adapter action string (e.g., "pre-task").
        is_guard: Whether this hook uses the shell fast-path guard
            (only for Write/Edit hooks that need to check for active
            deliver sessions before spawning Python).
    """

    event: str
    matcher: str | None
    action: str
    is_guard: bool = False


# Canonical hook event definitions -- the ONLY place these are defined.
# Order matters: PreToolUse/Agent must come before Write/Edit guards.
HOOK_EVENTS: tuple[HookEvent, ...] = (
    HookEvent(event="PreToolUse", matcher="Agent", action="pre-task"),
    HookEvent(event="PreToolUse", matcher="Write", action="pre-write", is_guard=True),
    HookEvent(event="PreToolUse", matcher="Edit", action="pre-edit", is_guard=True),
    HookEvent(event="PostToolUse", matcher="Agent", action="post-tool-use"),
    HookEvent(event="SubagentStop", matcher=None, action="subagent-stop"),
    HookEvent(event="SessionStart", matcher="startup", action="session-start"),
    HookEvent(event="SubagentStart", matcher=None, action="subagent-start"),
)

# The distinct event types DES registers (for validation).
HOOK_EVENT_TYPES: frozenset[str] = frozenset(h.event for h in HOOK_EVENTS)


def generate_hook_config(
    command_fn: callable,
    guard_command_fn: callable | None = None,
) -> dict[str, list[dict]]:
    """Generate hooks config in Claude Code hooks.json format.

    Args:
        command_fn: Callable(action: str) -> str that produces the
            hook command string for a given action. Each distribution
            path provides its own (plugin vs installer paths).
        guard_command_fn: Optional callable(action: str) -> str for
            Write/Edit guard hooks that use shell fast-path. If None,
            guard hooks use command_fn instead (no fast-path).

    Returns:
        Dict mapping event names to lists of hook entries, matching
        the Claude Code hooks.json schema:
        {"EventName": [{"matcher": "...", "hooks": [{"type": "command", "command": "..."}]}]}
    """
    config: dict[str, list[dict]] = {}

    for hook_event in HOOK_EVENTS:
        if hook_event.is_guard and guard_command_fn is not None:
            command = guard_command_fn(hook_event.action)
        else:
            command = command_fn(hook_event.action)

        entry: dict = {"hooks": [{"type": "command", "command": command}]}
        if hook_event.matcher is not None:
            entry["matcher"] = hook_event.matcher

        config.setdefault(hook_event.event, []).append(entry)

    return config


def build_guard_command(python_cmd: str) -> str:
    """Build the shell fast-path guard command template for Write/Edit hooks.

    The guard:
    1. Buffers stdin (hook input JSON)
    2. If the target is execution-log.json, always invokes Python (unconditional)
    3. Otherwise, checks for deliver-session.json -- exits 0 if absent (fast path)
    4. If present, invokes Python for full DES enforcement

    Args:
        python_cmd: The full Python command string (PYTHONPATH=... python3 -m ...)
            WITHOUT the action suffix. The action will be appended by the caller.

    Returns:
        Shell command template string. The caller must format it with the action.
    """
    return (  # noqa: UP032 — .format() required for shell template with literal braces
        "INPUT=$(cat); "
        "echo \"$INPUT\" | grep -q 'execution-log\\.json' && "
        '{{ echo "$INPUT" | {python_cmd}; exit $?; }}; '
        "test -f .nwave/des/deliver-session.json || exit 0; "
        'echo "$INPUT" | {python_cmd}'
    ).format(python_cmd=python_cmd)


def is_des_hook_entry(hook_entry: dict) -> bool:
    """Check if a hook entry is a DES hook.

    Supports both old flat format and new nested format:
    - Old flat: {"command": "...claude_code_hook_adapter..."}
    - New nested: {"hooks": [{"type": "command", "command": "...claude_code_hook_adapter..."}]}

    Args:
        hook_entry: Hook entry dictionary from settings JSON.

    Returns:
        True if entry is a DES hook.
    """
    # Check old flat format
    if "claude_code_hook_adapter" in hook_entry.get("command", ""):
        return True
    # Check new nested format
    for h in hook_entry.get("hooks", []):
        if "claude_code_hook_adapter" in h.get("command", ""):
            return True
    return False
