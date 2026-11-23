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
from collections.abc import Callable
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


#: The event names the hook CLI accepts (its argparse choices), listed once: a command takes its event from here.
EVENT_NAMES: tuple[str, ...] = tuple(dict.fromkeys(row.event for row in HOOK_EVENTS))

#: The kept events Copilot registers. Copilot spells an event key in camelCase; the command keeps the kept name.
COPILOT_EVENTS: tuple[str, ...] = ("PreToolUse",)


#: The kept events Cursor registers. Cursor reads a camelCase key (preToolUse); the command keeps the kept name.
CURSOR_EVENTS: tuple[str, ...] = ("PreToolUse",)


def copilot_event_key(event: str) -> str:
    """The key Copilot reads for a kept event name: the same name with a lower-case first letter."""
    return event[:1].lower() + event[1:]


def _kept_event(event: str) -> str:
    """The event name unchanged when the hook CLI accepts it; otherwise a refusal with WHAT, WHY and HOW."""
    if event not in EVENT_NAMES:
        raise ValueError(
            f"WHAT: {event!r} is not an event name the hook CLI accepts. WHY: a command that names it exits 2 "
            f"and the host denies every tool. HOW: use one of {', '.join(EVENT_NAMES)}."
        )
    return event


#: Hosts that receive kept registrations (fact F419). amp, pi and omp are not listed: their installers write TypeScript guard
#: extensions that are fully rewritten from a template on each install, so they hold no stale nWave entry (checked by
#: reading their code only, not by running them).
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

#: The version Copilot's hook format declares. Every documented Copilot hook file carries "version": 1 (card t-0559).
COPILOT_HOOK_VERSION: int = 1


def _with_copilot_version(document: dict[str, Any]) -> dict[str, Any]:
    """The Copilot document with "version": 1 first. A document that declares another version is refused, never rewritten.

    A file another tool wrote with a different version is not nWave's to rewrite, so it is refused before any write,
    with the version it holds and the one Copilot reads.
    """
    version = document.get("version", COPILOT_HOOK_VERSION)
    if type(version) is not int or version != COPILOT_HOOK_VERSION:
        raise ValueError(
            f'"version" in the copilot hook file is {version!r}, not {COPILOT_HOOK_VERSION}: Copilot reads version '
            f"{COPILOT_HOOK_VERSION} hook files and nWave never rewrites another schema"
        )
    rest = {key: value for key, value in document.items() if key != "version"}
    return {"version": COPILOT_HOOK_VERSION, **rest}


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


def shell_word(interpreter: str) -> str:
    """One shell word that runs the interpreter at that path.

    A path under $HOME is double-quoted with the $HOME left for the shell to expand:
    single quotes stop that expansion, so the shell would look for a literal "$HOME"
    directory and exit 127. The rest of the path has the characters that are special
    inside double quotes escaped, so a space in the path still reaches the shell as one
    word.
    Every other path is quoted as it always was.
    """
    home_prefix = "$HOME/"
    if interpreter.startswith(home_prefix):
        rest = re.sub(r'(["$`\\])', r"\\\1", interpreter[len(home_prefix) :])
        return f'"{home_prefix}{rest}"'
    return shlex.quote(interpreter)


# How an interpreter path is written as a shell word: the writer uses shell_word.
Spelling = Callable[[str], str]


def hook_command(
    interpreter: str, event: str, host: str, spell: Spelling = shell_word
) -> str:
    """Shell command of one registration: interpreter, -m nwave_ai.hooks EVENT --host H."""
    return f"{spell(interpreter)} -m nwave_ai.hooks {event} --host {host}"


_REGISTERED_COMMAND = re.compile(
    r'(?P<interpreter>"(?:[^"\\]|\\.)*"|\'[^\']*\'|[^\s\'"]+)'
    r" -m nwave_ai\.hooks (?P<event>[A-Za-z]+) --host (?P<host>[a-z]+)"
)

# The Claude guard wrapper of a plain command, built by the writer's own template: the plain command appears twice,
# and a whole Claude command is owned only when both occurrences are the same plain command.
_GUARD_SLOT = "\x00plain-command\x00"
_GUARD_PREFIX, _GUARD_MIDDLE, _GUARD_SUFFIX = build_guard_command(_GUARD_SLOT).split(
    _GUARD_SLOT
)
_GUARDED_COMMAND = re.compile(
    re.escape(_GUARD_PREFIX)
    + r"(?P<plain>.+)"
    + re.escape(_GUARD_MIDDLE)
    + r"(?P=plain)"
    + re.escape(_GUARD_SUFFIX),
    re.DOTALL,
)


def _shell_word_value(token: str) -> str:
    """The path a shell word names: the inverse of shell_word, read the way the shell reads it.

    Inside double quotes a backslash escapes only $, backtick, double quote and backslash; the
    quotes are removed. Inside single quotes everything is literal. Any other word is read by
    shlex, which is correct for the unquoted words the writer never produces for an interpreter.
    """
    if len(token) >= 2 and token[0] == token[-1] == '"':
        body = token[1:-1]
        out: list[str] = []
        index = 0
        while index < len(body):
            char = body[index]
            if char == "\\" and index + 1 < len(body) and body[index + 1] in '$`"\\':
                out.append(body[index + 1])
                index += 2
                continue
            out.append(char)
            index += 1
        return "".join(out)
    if len(token) >= 2 and token[0] == token[-1] == "'":
        return token[1:-1]
    return shlex.split(token)[0]


def _claude_command(row: HookEvent, interpreter: str, spell: Spelling) -> str:
    """Claude command of one row; guard rows start Python only when a decision is needed."""
    plain = hook_command(interpreter, row.event, "claude", spell)
    return build_guard_command(plain) if row.is_guard else plain


def entries(
    host: str, interpreter: str, spell: Spelling = shell_word
) -> tuple[tuple[str, dict[str, Any]], ...]:
    """(event key, canonical entry) for each kept registration of one host (F419).

    ``spell`` is the interpreter spelling the entries use; the writer uses shell_word.
    """

    if host == "claude":
        pairs: list[tuple[str, dict[str, Any]]] = []
        for row in HOOK_EVENTS:
            group: dict[str, Any] = {
                "hooks": [
                    {
                        "type": "command",
                        "command": _claude_command(row, interpreter, spell),
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
                    "command": hook_command(interpreter, "PreToolUse", host, spell),
                }
            ],
        }
        return (("PreToolUse", group),)
    if host == "cursor":
        return tuple(
            (
                copilot_event_key(event),
                _cursor_entry(interpreter, spell, _kept_event(event)),
            )
            for event in CURSOR_EVENTS
        )
    if host == "copilot":
        return tuple(
            (
                copilot_event_key(event),
                _copilot_entry(interpreter, spell, _kept_event(event)),
            )
            for event in COPILOT_EVENTS
        )
    raise ValueError(f"unknown host {host!r}")


def _cursor_entry(
    interpreter: str, spell: Spelling, command_event: str
) -> dict[str, Any]:
    """Cursor entry of one registration: the flat command entry under the camelCase key."""
    command = hook_command(interpreter, command_event, "cursor", spell)
    return {"command": command, "matcher": CURSOR_MATCHER, "timeout": 30}


def _copilot_entry(
    interpreter: str, spell: Spelling, command_event: str
) -> dict[str, Any]:
    """Copilot entry of one registration: the nested matcher group the spike proved (FS-1)."""
    command = hook_command(interpreter, command_event, "copilot", spell)
    return {
        "matcher": COPILOT_MATCHER,
        "hooks": [{"type": "command", "bash": command, "timeoutSec": 30}],
    }


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


def _is_installed_spelling(interpreter: str) -> bool:
    """True for the interpreter spellings an install writes: python3, a HOME-prefixed path, or an absolute path."""
    if interpreter == "python3" or interpreter.startswith("$HOME"):
        return True
    return interpreter.startswith("/") or PureWindowsPath(interpreter).is_absolute()


def owned(entry: object, event: str, host: str) -> bool:
    """True only for an entry whose whole command is an nWave command of this host and of ``event``.

    The whole command must be ``<interpreter> -m nwave_ai.hooks EVENT --host HOST`` with the interpreter spelled the
    way an install writes it, or, for Claude's guarded rows, the guard wrapper an install writes around that command.
    Nothing may come before or after it. The matcher, the timeout and the interpreter path do not decide ownership:
    an older nWave install wrote them differently, and an entry that points at a deleted environment is still nWave's.
    A foreign command that only contains the mark text (``echo '<mark>'``, ``<mark>; echo x``) is not owned.
    """
    if not isinstance(entry, dict):
        return False
    command = _entry_command(entry)
    if not isinstance(command, str):
        return False
    plain = _plain_command(command, host)
    if plain is None:
        return False
    match = _REGISTERED_COMMAND.fullmatch(plain)
    if match is None or match["host"] != host:
        return False
    if not _is_installed_word(match["interpreter"]):
        return False
    if host in ("copilot", "cursor"):
        return _is_kept_camel_key(event, match["event"], host)
    return match["event"] == event


def _plain_command(command: str, host: str) -> str | None:
    """The plain nWave command a whole entry command runs: itself, or for Claude the guard wrapper around it."""
    if host == "claude":
        guarded = _GUARDED_COMMAND.fullmatch(command)
        if guarded is not None:
            return guarded["plain"]
    return command


def _is_installed_word(token: str) -> bool:
    """True when the interpreter word is exactly one spelling an install writes for an installed interpreter path.

    The word must be the quoting of its own value by one of the writer's spellings, so a word that only resembles
    an install's (extra quotes, a shell operator inside double quotes) is refused.
    """
    try:
        value = _shell_word_value(token)
    except (ValueError, IndexError):
        return False
    if not _is_installed_spelling(value):
        return False
    return token in {shell_word(value), shlex.quote(value)}


def _is_kept_camel_key(key: str, command_event: str, host: str) -> bool:
    """True when ``key`` is the camelCase key of a kept event and the command names that event or that key.

    The command names the kept event, or the camelCase key an earlier nWave wrote (the old spelling the hook
    CLI refuses); both are nWave's, so a reinstall replaces the old one instead of keeping it beside the new.
    """
    events = COPILOT_EVENTS if host == "copilot" else CURSOR_EVENTS
    kept = next((event for event in events if copilot_event_key(event) == key), None)
    return kept is not None and command_event in (kept, key)


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


def _wrapped_copilot(document: dict[str, Any]) -> dict[str, Any]:
    """The Copilot document with its event map under the top-level ``hooks`` object.

    An earlier nWave wrote the event map at the top level, which Copilot rejects ("hooks must be an object").
    Every top-level list is an event of that map: it moves under ``hooks``, before the entries already there.
    """
    hooks = document.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError('"hooks" in the copilot hook file is not an object')
    legacy = {key: value for key, value in document.items() if isinstance(value, list)}
    if not legacy:
        return document
    moved = dict(hooks)
    for key, value in legacy.items():
        present = moved.get(key, [])
        if not isinstance(present, list):
            raise ValueError(f"{key!r} in the copilot hook file is not a list")
        moved[key] = value + present
    rest = {key: value for key, value in document.items() if key not in legacy}
    return {**rest, "hooks": moved}


def refusal_by_host(document: dict[str, Any], host: str) -> str | None:
    """Why the host would reject this hook document, or None. Only Copilot validates the shape of its file."""
    if host == "copilot" and not isinstance(document.get("hooks"), dict):
        return (
            "Copilot rejects this file (hooks: hooks must be an object): the event map must sit "
            'under a top-level "hooks" object'
        )
    return _refused_event(document)


def _refused_event(document: object) -> str | None:
    """A nWave command in the document that names an event the hook CLI refuses (it exits 2), or None."""
    if isinstance(document, dict):
        return next(
            (found for value in document.values() if (found := _refused_event(value))),
            None,
        )
    if isinstance(document, list):
        return next(
            (found for value in document if (found := _refused_event(value))), None
        )
    if isinstance(document, str):
        match = _REGISTERED_COMMAND.search(document)
        if match is not None and match["event"] not in EVENT_NAMES:
            return (
                f"the command names the event {match['event']!r}, which the hook CLI refuses (exit 2, "
                f"every tool denied); it accepts {', '.join(EVENT_NAMES)}"
            )
    return None


def merge(document: dict[str, Any], host: str, interpreter: str) -> dict[str, Any]:
    """The host document with the kept entries replaced; every other entry is kept."""
    result: dict[str, Any] = deepcopy(document)
    if host == "copilot":
        result = _with_copilot_version(_wrapped_copilot(result))
    if host == "cursor":
        result.setdefault("version", 1)
    container = result.setdefault("hooks", {})
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
    if host == "copilot":
        result = _wrapped_copilot(result)
    container = result.get("hooks")
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
