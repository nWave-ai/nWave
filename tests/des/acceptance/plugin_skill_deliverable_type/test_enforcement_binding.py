"""Enforcement-gate binding (LIVE regression guards) -- plugin-skill-deliverable-type.

Binds ONLY the existing-behaviour-preservation scenarios from
``deliverable-type-enforcement.feature`` -- the ones that assert the app-code
enforcement path is 100% unchanged by this feature (ADR-PST-001 "app-code paths
byte-identical"). These are GREEN today against the production policy (the
``__SCAFFOLD__`` exempt branch raises ONLY for plugin/skill, never for these
cases), so they are the committable resting state and a genuine regression net.

The not-yet-implemented scenarios (plugin/skill exemption -- incl. the
`@walking_skeleton`) live in ``test_enforcement_pending.py`` under a module-level
skip, the One-at-a-Time way (ADR-025): DELIVER unskips them as it greens the
policy short-circuit. SPIKE was DISCARDED (no promoted skeleton), so the WS is
parked-skipped at DISTILL and DELIVER greens it first.

`scenario()` (singular) binds each guard by exact title -- a per-scenario binding
that lets the RED siblings be parked separately without skipping these guards.
"""

from pytest_bdd import scenario

from tests.des.acceptance.plugin_skill_deliverable_type.steps.steps_plugin_skill import *  # noqa: F403


_FEATURE = "deliverable-type-enforcement.feature"


@scenario(_FEATURE, "An application project keeps planned-step work under discipline")
def test_application_stays_policed() -> None:
    """App-code dispatch with a planned step and no markers stays BLOCKED."""


@scenario(
    _FEATURE, "A project with no declared deliverable keeps work under discipline"
)
def test_unset_stays_policed() -> None:
    """Unset deliverable fails safe -> stays BLOCKED (existing behaviour)."""


@scenario(_FEATURE, "A mis-spelled deliverable type quietly re-imposes discipline")
def test_typo_stays_policed() -> None:
    """A typo'd type is not exempt -> stays BLOCKED (closed exempt set)."""


@scenario(_FEATURE, "A mis-cased deliverable type is not honoured and discipline holds")
def test_mis_cased_stays_policed() -> None:
    """'Plugin' (case mismatch) is not exempt -> stays BLOCKED (case-sensitive)."""


@scenario(_FEATURE, "An explicit exemption still releases an application dispatch")
def test_explicit_exemption_still_releases() -> None:
    """The per-dispatch DES-ENFORCEMENT exempt marker still short-circuits."""


@scenario(_FEATURE, "An ordinary dispatch with no planned step is never policed")
def test_no_step_never_policed() -> None:
    """A dispatch with no planned step is never blocked, regardless of type."""
