"""Domain types for the E7 install-registration slice.

Every domain noun used in the E7 `.feature` files is expressed once here as a
typed enum or constant (Mandate-12 criterion 1). Step bodies and the composition
consume these typed parameters — no raw `str` where a domain enum exists.

E7 is the install-wiring + registration-gate slice: install (and the
`attribution on|off` CLI) must register a Bash commit-attribution hook entry in
`~/.claude/settings.json`, gated by `attribution.enabled`, coexisting with the
existing DES Bash execution-log guard. The observable is the settings.json
`hooks.PreToolUse` array CONTENT.

The two observable markers are expressed test-side (NOT imported from production)
so the AT asserts on the OBSERVABLE settings.json content, never on a production
internal (S2 — driving-port-only):

  * `GUARD_MARKER` — the substring identifying the existing `pre-bash`
    execution-log guard, so coexistence is asserted on real content.
  * `ATTRIBUTION_ACTION` — the action token the commit-attribution entry must
    route to (`pre-commit-attribution`), so the registered entry is recognized.
"""

from __future__ import annotations

from enum import Enum


class AttributionChoice(str, Enum):
    """The operator's attribution preference — the registration gate (O-4).

    ENABLED  — the operator wants commits credited; install registers the
               commit-attribution hook.
    DISABLED — the operator opted out; install registers no commit-attribution
               hook (the gate is closed).
    """

    ENABLED = "enabled"
    DISABLED = "disabled"


class HomeShape(str, Enum):
    """The shape of the sandboxed nWave home a scenario starts from.

    GUARD_PRESENT — `~/.claude/settings.json` exists with the DES Bash
                    execution-log guard already registered (the normal post-DES
                    install state the attribution hook must coexist with).
    NO_CLAUDE     — `~/.claude/` is absent (Claude Code not installed → Q5
                    warn+skip).
    CORRUPT       — `~/.claude/settings.json` exists but is not valid JSON
                    (must be left untouched, never stomped).
    """

    GUARD_PRESENT = "guard_present"
    NO_CLAUDE = "no_claude"
    CORRUPT = "corrupt"


# The substring that identifies the existing DES `pre-bash` execution-log guard
# in a settings.json hooks.PreToolUse entry. Coexistence is asserted by this
# marker still being present after attribution registration. Test-side observable
# (the production marker is `# des-hook:pre-bash`), never imported (S2).
GUARD_MARKER = "des-hook:pre-bash"

# The action token the commit-attribution hook entry must route to. The new Bash
# entry dispatches the (E6-extended) `pre-tool-use` adapter; the install-time
# registration tags it with this distinct action so it is recognizable and
# removable independently of the `pre-bash` guard. Test-side observable, never
# imported from the registration module (S2 — driving-port-only).
ATTRIBUTION_ACTION = "pre-commit-attribution"

# A representative operator-authored Bash hook entry, used to prove registration
# appends without stomping a neighbour the operator added themselves.
OPERATOR_BASH_HOOK: dict = {
    "matcher": "Bash",
    "hooks": [
        {"type": "command", "command": "echo operator-owned-guard"},
    ],
}

# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body a
# single typed lookup plus a single composition call (Mandate-12 criterion 3).

CHOICE_BY_PHRASE: dict[str, AttributionChoice] = {
    "enable attribution": AttributionChoice.ENABLED,
    "disable attribution": AttributionChoice.DISABLED,
}

# The adjective form used in `installed with attribution {state}` and
# `turns attribution {state}` (e.g. "enabled"/"disabled", "on"/"off").
CHOICE_BY_STATE: dict[str, AttributionChoice] = {
    "enabled": AttributionChoice.ENABLED,
    "disabled": AttributionChoice.DISABLED,
    "on": AttributionChoice.ENABLED,
    "off": AttributionChoice.DISABLED,
}

HOME_BY_PHRASE: dict[str, HomeShape] = {
    "where the commit guard is already registered": HomeShape.GUARD_PRESENT,
    "with no Claude configuration": HomeShape.NO_CLAUDE,
    "whose settings are corrupt": HomeShape.CORRUPT,
}
