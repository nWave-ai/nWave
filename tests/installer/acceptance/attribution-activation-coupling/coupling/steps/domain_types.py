"""Domain types for the attribution-activation-coupling acceptance suite.

Mandate-12 criterion 1: every domain noun used in the Gherkin scenarios is
expressed here ONCE as a typed enum / dataclass / NewType. Composition-service
signatures (in ``composition.py``) consume these types — never raw ``str``
where an enum exists. Step bodies coerce Gherkin literals into these types via
``pytest_bdd.parsers`` converters, so the DSL emerges from the type system
rather than from a decorator-per-literal explosion.

Feature contract source of truth:
- ``docs/feature/attribution-activation-coupling/feature-delta.md`` (DESIGN, §9 AB-1..AB-11)
- ``docs/product/architecture/ADR-CA-007-attribution-coupled-to-activation.md``

Where a domain noun already has a canonical typed home in the
activation-gating suite (``RepoActivationState`` ⇔ marker x mode), this module
imports / reuses it rather than re-deriving (Mandate-12 SSOT, step-reuse).
"""

from __future__ import annotations

from enum import Enum


class RepoActivationState(Enum):
    """The per-repo activation posture a commit is attempted under.

    Collapses the (marker x global-mode) truth table into the three
    behaviourally-distinct cases the attribution scope-change cares about:

    - ``ACTIVE``        — marker enabled (or mode=all) → nWave active here.
    - ``INACTIVE_STICKY`` — sticky ``enabled_for_repo: false`` opt-out.
    - ``UNMARKED``      — no marker, opt-in default → inactive (a non-nWave repo).
    """

    ACTIVE = "active"
    INACTIVE_STICKY = "inactive-sticky"
    UNMARKED = "unmarked"


class AttributionPreference(Enum):
    """The SSOT preference in ``~/.nwave/global-config.json`` → ``attribution.enabled``."""

    ON = "on"
    OFF = "off"
    UNSET = "unset"


class SettingsResidue(Enum):
    """The shape of any pre-existing ``settings.json attribution.commit`` block.

    Drives the upgrade-migration scenarios (AB-4 / AB-5). The classifier
    baseline distinguishes a value nWave wrote (safe to clean) from one the
    user authored (never stomp).
    """

    NWAVE_MANAGED = "nwave-managed"  # exactly the managed payload → clean on upgrade
    USER_MODIFIED = "user-modified"  # developer authored → preserve untouched
    ABSENT = "absent"  # no attribution.commit at all


class CommitForm(Enum):
    """The shape of the Bash ``git commit`` command Claude issues (AB-1).

    Both are covered by the CA-006 rewriter; the dual trailer outcome must hold
    for each.
    """

    DASH_M = "dash-m"  # git commit -m "msg"
    AND_CHAIN = "and-chain"  # git add -A && git commit -m "msg"


class SettingsAvailability(Enum):
    """The readability of ``~/.claude/settings.json`` (AB-11 fail-open matrix)."""

    PRESENT = "present"  # readable JSON
    ABSENT = "absent"  # ~/.claude/ missing (Claude Code not installed)
    CORRUPT = "corrupt"  # exists but not valid JSON


class ToggleAction(Enum):
    """A ``nwave-ai attribution`` verb (AB-6 / AB-7 / AB-8)."""

    ON = "on"
    OFF = "off"
    STATUS = "status"


class HookRegistration(Enum):
    """Whether the ``pre-commit-attribution`` PreToolUse entry is registered."""

    REGISTERED = "registered"
    UNREGISTERED = "unregistered"


class TrailerOutcome(Enum):
    """The observable trailer effect on a committed message (AB-1..AB-3)."""

    DUAL_TRAILER = "dual-trailer"  # exactly 2 Co-Authored-By (Claude + nWave)
    NO_TRAILER = "no-trailer"  # message unchanged; no nWave credit


class DeprecatedKeyLocation(Enum):
    """Where ``includeCoAuthoredBy`` is read from (AB-9 / DDD-7 bug-fix).

    The current (buggy) code reads it nested under ``settings["attribution"]``;
    Claude Code stores it ``TOP_LEVEL``. The doctor must read TOP_LEVEL.
    """

    TOP_LEVEL = "top-level"
    NESTED_UNDER_ATTRIBUTION = "nested-under-attribution"


# The managed commit payload (mirror of attribution_utils.NWAVE_MANAGED_COMMIT)
# expressed as a domain constant so step bodies never inline the literal.
NWAVE_MANAGED_COMMIT = (
    "🤖 Generated with Claude Code\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>\n"
    "Co-Authored-By: nWave <nwave@nwave.ai>"
)

USER_AUTHORED_COMMIT = "Co-Authored-By: Alice <alice@example.com>"
