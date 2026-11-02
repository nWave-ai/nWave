"""The kept hook set: the event table the shipped product registers.

Owned by S2 (kept hook set decision). Four event types and nine matcher/action
rows. Each row is the matching row of scripts/shared/hook_definitions.py
HOOK_EVENTS, restricted to the kept set: the retired post-tool-use and
subagent-start actions and the UserPromptSubmit array are not listed.

This module imports nothing from the des package, so it satisfies the platform
import rule as every other nwave_ai platform module does.
"""

from __future__ import annotations

import re
import shlex
from copy import deepcopy
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any

from nwave_ai.hooks.guard import build_guard_command


@dataclass(frozen=True)
class HookEvent:
    """One hook registration: event type, matcher, action, guard flag and shell command.

    ``shell_command`` is the verbatim shell command when set, as in the SSOT
    scripts/shared/hook_definitions.py ``HookEvent``; ``None`` for the kept rows.
    """

    event: str
    matcher: str | None
    action: str
    is_guard: bool = False
    shell_command: str | None = None


HOOK_EVENTS: tuple[HookEvent, ...] = (
    HookEvent(event="PreToolUse", matcher="Agent", action="pre-task"),
    HookEvent(event="PreToolUse", matcher="SendMessage", action="pre-tool-use"),
    HookEvent(
        event="PreToolUse", matcher="TaskCreate|TaskUpdate", action="pre-tool-use"
    ),
    HookEvent(event="PreToolUse", matcher="Write", action="pre-write", is_guard=True),
    HookEvent(event="PreToolUse", matcher="Edit", action="pre-edit", is_guard=True),
    HookEvent(event="PreToolUse", matcher="Bash", action="pre-tool-use"),
    HookEvent(event="SubagentStop", matcher=None, action="subagent-stop"),
    HookEvent(event="SessionStart", matcher=None, action="session-start"),
    HookEvent(event="SessionEnd", matcher=None, action="session-end"),
)

#: The four event types the kept hook set registers, derived from HOOK_EVENTS.
HOOK_EVENT_TYPES: frozenset[str] = frozenset(row.event for row in HOOK_EVENTS)


#: Hosts that receive kept registrations (fact F419).
HOSTS: tuple[str, ...] = ("claude", "codex", "cursor", "copilot")

#: Matcher of the shell registration on Codex, Cursor and Copilot (fact F419).
CODEX_MATCHER = "^exec_command$|^Bash$"
CURSOR_MATCHER = "Shell|Write|Edit|Delete"
COPILOT_MATCHER = ".*"

#: Hook file of each host, relative to that host's configuration directory.
HOOK_FILE: dict[str, str] = {
    "claude": "settings.json",
    "codex": "hooks.json",
    "cursor": "hooks.json",
    "copilot": "hooks/nwave-hooks.json",
}


def interpreter_for_shell(path: str, *, windows: bool) -> str:
    """Spell an absolute interpreter path for the POSIX shell that runs hook commands.

    On Windows the shell is Git for Windows bash, which reads a backslash as an
    escape and a single-quoted backslash as a literal, so the path is spelled with
    forward slashes (``C:/...``) and the extended-length ``\\\\?\\`` prefix is
    dropped. Elsewhere the path is returned unchanged.
    """
    if not windows:
        return path
    spelled = path.replace("\\", "/")
    if spelled.startswith("//?/UNC/"):
        return "//" + spelled[len("//?/UNC/") :]
    if spelled.startswith("//?/"):
        return spelled[len("//?/") :]
    return spelled


def hook_command(interpreter: str, event: str, host: str) -> str:
    """Shell command of one registration: interpreter, -m nwave_ai.hooks EVENT --host H."""
    return f"{shlex.quote(interpreter)} -m nwave_ai.hooks {event} --host {host}"


_REGISTERED_COMMAND = re.compile(
    r"(?P<interpreter>'[^']*'|[^\s']+)"
    r" -m nwave_ai\.hooks (?P<event>[A-Za-z]+) --host (?P<host>[a-z]+)"
)


def _claude_command(row: HookEvent, interpreter: str) -> str:
    """Claude command of one row; guard rows start Python only when a decision is needed."""
    plain = hook_command(interpreter, row.event, "claude")
    return build_guard_command(plain) if row.is_guard else plain


def entries(host: str, interpreter: str) -> tuple[tuple[str, dict[str, Any]], ...]:
    """(event key, canonical entry) for each kept registration of one host (F419)."""
    if host == "claude":
        pairs: list[tuple[str, dict[str, Any]]] = []
        for row in HOOK_EVENTS:
            group: dict[str, Any] = {
                "hooks": [
                    {
                        "type": "command",
                        "command": _claude_command(row, interpreter),
                    }
                ]
            }
            if row.matcher is not None:
                group = {"matcher": row.matcher, **group}
            pairs.append((row.event, group))
        return tuple(pairs)
    if host == "codex":
        group = {
            "matcher": CODEX_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "command": hook_command(interpreter, "PreToolUse", host),
                }
            ],
        }
        return (("PreToolUse", group),)
    if host == "cursor":
        command = hook_command(interpreter, "preToolUse", host)
        entry = {"command": command, "matcher": CURSOR_MATCHER, "timeout": 30}
        return (("preToolUse", entry),)
    if host == "copilot":
        command = hook_command(interpreter, "preToolUse", host)
        group = {
            "matcher": COPILOT_MATCHER,
            "hooks": [{"type": "command", "bash": command, "timeoutSec": 30}],
        }
        return (("preToolUse", group),)
    raise ValueError(f"unknown host {host!r}")


def _entry_command(entry: dict[str, Any]) -> object:
    if "command" in entry:
        return entry["command"]
    children = entry.get("hooks")
    if (
        isinstance(children, list)
        and len(children) == 1
        and isinstance(children[0], dict)
    ):
        return children[0].get("command", children[0].get("bash"))
    return None


def owned(entry: object, event: str, host: str) -> bool:
    """True only for an entry equal to a canonical kept entry of this event and host."""
    if not isinstance(entry, dict):
        return False
    command = _entry_command(entry)
    if not isinstance(command, str):
        return False
    match = _REGISTERED_COMMAND.search(command)
    if match is None or match["event"] != event or match["host"] != host:
        return False
    try:
        interpreter = shlex.split(match["interpreter"])[0]
    except (ValueError, IndexError):
        return False
    if not (interpreter.startswith("/") or PureWindowsPath(interpreter).is_absolute()):
        return False
    return any(
        key == event and entry == canonical
        for key, canonical in entries(host, interpreter)
    )


def _without_owned(existing: list[Any], event: str, host: str) -> list[Any]:
    """The entries that are not kept-owned.

    An owned handler is removed from its matcher group; foreign handlers that share
    the group stay where they are, and a group left with no handler is dropped.
    """
    kept: list[Any] = []
    for entry in existing:
        if owned(entry, event, host):
            continue
        handlers = entry.get("hooks") if isinstance(entry, dict) else None
        if isinstance(handlers, list):
            group = {key: value for key, value in entry.items() if key != "hooks"}
            remaining = [
                handler
                for handler in handlers
                if not owned({**group, "hooks": [handler]}, event, host)
            ]
            if not remaining:
                continue
            entry = {**entry, "hooks": remaining}
        kept.append(entry)
    return kept


def merge(document: dict[str, Any], host: str, interpreter: str) -> dict[str, Any]:
    """The host document with the kept entries replaced; every other entry is kept."""
    result: dict[str, Any] = deepcopy(document)
    if host == "cursor":
        result.setdefault("version", 1)
    container = result if host == "copilot" else result.setdefault("hooks", {})
    wanted: dict[str, list[dict[str, Any]]] = {}
    for key, entry in entries(host, interpreter):
        wanted.setdefault(key, []).append(entry)
    keys = set(wanted) | {
        key for key, value in container.items() if isinstance(value, list)
    }
    for key in sorted(keys):
        existing = container.get(key, [])
        if not isinstance(existing, list):
            raise ValueError(f"{key!r} in the {host} hook file is not a list")
        kept = _without_owned(existing, key, host)
        updated = kept + wanted.get(key, [])
        if updated:
            container[key] = updated
        elif existing:
            container.pop(key)
    return result


def without_registrations(document: dict[str, Any], host: str) -> dict[str, Any]:
    """The host document with every kept registration removed; every other entry is kept."""
    result: dict[str, Any] = deepcopy(document)
    container = result if host == "copilot" else result.get("hooks")
    if not isinstance(container, dict):
        return result
    for key in sorted(container):
        existing = container[key]
        if not isinstance(existing, list):
            continue
        kept = _without_owned(existing, key, host)
        if kept:
            container[key] = kept
        else:
            container.pop(key)
    return result
