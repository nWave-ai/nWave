"""Typed domain vocabulary for the attribution-migration acceptance suite.

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed once
here as a typed enum / NewType / frozen dataclass. Step bodies (steps_attribution.py)
consume these typed parameters and delegate to the composition root — no raw `str`
where a domain enum exists, no business logic in step bodies.

The "attribution credit", "legacy hook", "Claude settings", and "nWave preference
store" are the four domain objects this feature reasons about. The locked managed
credit string (ADR-CA-004) is the single source of truth, re-exported from the
production module so the tests cannot drift from the shipped payload.
"""

from __future__ import annotations

from enum import Enum

from scripts.install.attribution_utils import (
    NWAVE_MANAGED_COMMIT,
    NWAVE_MANAGED_PR,
)


# The locked managed credit (ADR-CA-004) — re-exported from production so the
# acceptance suite asserts against the SAME constant the installer writes.
DUAL_TRAILER_COMMIT: str = NWAVE_MANAGED_COMMIT
DUAL_TRAILER_PR: str = NWAVE_MANAGED_PR


class AttributionState(Enum):
    """Whether nWave attribution is active for the developer."""

    ON = "on"
    OFF = "off"


class SettingsScenario(Enum):
    """The starting shape of the developer's Claude settings + nWave store.

    Drives the Given preconditions: each value is a distinct world the
    installer/CLI must handle.
    """

    FRESH = "fresh"  # no Claude settings, no nWave store
    THEME_ONLY = "theme_only"  # Claude settings has an unrelated key only
    NWAVE_PRIOR = "nwave_prior"  # nWave already wrote the managed credit
    USER_CUSTOM = "user_custom"  # the developer authored their own credit
    LEGACY_HOOK = "legacy_hook"  # legacy prepare-commit-msg shim installed
    MALFORMED = "malformed"  # Claude settings is not valid JSON
    CLAUDE_ABSENT = "claude_absent"  # ~/.claude/ directory does not exist


class CliAction(Enum):
    """The attribution CLI verbs (signature unchanged by this feature)."""

    ON = "on"
    OFF = "off"
    STATUS = "status"


class CreditOwner(Enum):
    """Who authored the credit currently recorded in Claude settings."""

    NWAVE = "nwave"  # the managed dual-trailer block
    USER = "user"  # a value the developer wrote themselves
    NONE = "none"  # no credit recorded
