"""Jev access: consent and key presence resolve to one state, and the missing-key message is written once.

Pure and stdlib only: no I/O, no environment reads, no import of nwdes or nwave_ai. The module
exists in two byte-identical copies: the skill copy, beside the Jev client that reaches every
host, and src/nwdes/jev_access.py, for the installer and the nwdes bundle. Edit either copy,
then copy it over the other; a test fails while the two differ.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


AUTHORIZED = "authorized"
UNAUTHORIZED = "unauthorized"
KEY_VARIABLE = "TYPESAFE_API_KEY"
GUIDE_URL = "https://github.com/nWave-ai/nWave/blob/main/docs/guides/configuring-jev.md"

# Per shell: (shell, command for this session, command that persists it). Quoted so that
# "<your key>" is one literal word in every shell; cmd reads an unquoted "<" as redirection.
SHELL_COMMANDS = (
    (
        "bash or zsh",
        "export TYPESAFE_API_KEY='<your key>'",
        "add that line to ~/.bashrc or ~/.zshrc",
    ),
    (
        "fish",
        "set -x TYPESAFE_API_KEY '<your key>'",
        "set -Ux TYPESAFE_API_KEY '<your key>'",
    ),
    (
        "PowerShell",
        "$env:TYPESAFE_API_KEY = '<your key>'",
        "[Environment]::SetEnvironmentVariable('TYPESAFE_API_KEY','<your key>','User')",
    ),
    (
        "Windows cmd",
        'set "TYPESAFE_API_KEY=<your key>"',
        'setx TYPESAFE_API_KEY "<your key>"',
    ),
)


class JevAccess(Enum):
    ACTIVE_WITH_KEY = "active-with-key"
    ACTIVE_WITHOUT_KEY = "active-without-key"
    UNAUTHORIZED = "unauthorized"


class JevWarning(NamedTuple):
    what: str
    why: str
    how: tuple[str, ...]


def key_is_set(value: str | None) -> bool:
    """The one rule for key presence: the variable's value is non-empty.

    The caller reads the environment and passes the value; this function never reads it.
    """
    return bool(value)


def resolve_access(consent: str, key_present: bool) -> JevAccess:
    """Refusal wins whatever the key; consent to use Jev needs the key to be set."""
    if consent == UNAUTHORIZED:
        return JevAccess.UNAUTHORIZED
    if consent == AUTHORIZED:
        return (
            JevAccess.ACTIVE_WITH_KEY if key_present else JevAccess.ACTIVE_WITHOUT_KEY
        )
    raise ValueError(
        f"WHAT: consent {consent!r} is not a Jev choice. "
        f"WHY: access is decided only for {AUTHORIZED!r} or {UNAUTHORIZED!r}. "
        "HOW: pass the value of the jev entry in .nwave/config.json as read by nwdes."
    )


def _shell_rows() -> tuple[str, ...]:
    rows: list[str] = []
    for shell, session, persistent in SHELL_COMMANDS:
        rows.append(f"  {shell}")
        rows.append(f"    this session: {session}")
        rows.append(f"    persistent:   {persistent}")
    return tuple(rows)


_MISSING_KEY = JevWarning(
    what=(
        f"Jev is on for this project but {KEY_VARIABLE} is not set in this process; "
        "Jev questions are skipped and nWave continues without Jev."
    ),
    why=(
        "Jev, a remote service, answers only requests that carry your key. nWave never "
        f"stores the key and only checks that {KEY_VARIABLE} is set. Consent (the jev "
        "entry in .nwave/config.json) and the key are separate settings."
    ),
    how=(
        f"set {KEY_VARIABLE} to the key you have from your Jev account, in the shell you "
        "start your coding host from. A host started before the change does not see the "
        "variable: start it again from that shell.",
        *_shell_rows(),
        "then check with: nwave-ai status (it prints key: set when the variable is visible).",
        "a tool kernel, such as a Python eval kernel, may not inherit the session "
        "environment: run the Jev client from a shell command instead.",
        'to stop Jev for this project instead: "jev": "unauthorized" in .nwave/config.json.',
        f"guide: {GUIDE_URL}",
    ),
)


def warning(access: JevAccess) -> JevWarning | None:
    """The missing-key message, or None: a refusal and a working key both stay silent."""
    if access is not JevAccess.ACTIVE_WITHOUT_KEY:
        return None
    return _MISSING_KEY


def render(warning_value: JevWarning) -> str:
    """The full WHAT / WHY / HOW text, without a trailing newline."""
    lines = [
        f"WHAT: {warning_value.what}",
        f"WHY: {warning_value.why}",
        "HOW:",
    ]
    lines.extend(f"  {line}" for line in warning_value.how)
    return "\n".join(lines)


def one_line(warning_value: JevWarning) -> str:
    """A one-line projection of the same warning, for a status line."""
    return f"{warning_value.what} Run nwave-ai status for how to set {KEY_VARIABLE}."
