"""Tier-A step definitions for the plugin/skill deliverable-type acceptance suite.

Mandate-12: every step body is <=2 statements, the final action statement is a
``composition.<method>(...)`` call, and no control flow appears in any body. The
DSL emerges from typed ``parsers.parse`` converters over the ``domain_types``
enums -- a handful of parameterized decorators cover the whole literal space
instead of a decorator-per-literal explosion.

State-mutating ``Then`` steps assert via ``assert_state_delta`` (Mandate 8) with
a port-exposed universe; pure-query ``Then`` steps assert on a single captured
port observable. Shared step-method NAMES are the cross-tier contract (Tier B
imports the composition vocabulary they drive).

Layer: 3 (subprocess/FS acceptance over a real tmp_path project). Per Mandate 9
+ 11 this layer is example-only -- no Hypothesis ``@given`` here; sad paths are
enumerated explicitly. The finite matrices (enforcement, detection) are covered
by ``@pytest.mark.parametrize`` in the companion spec modules (falsifier-gate:
finite, enumerable -> parametrize, not PBT).
"""

from __future__ import annotations

from nwave_ai.state_delta import assert_state_delta, set_to
from pytest_bdd import given, parsers, then, when

from tests.des.acceptance.plugin_skill_deliverable_type.steps.domain_types import (
    ConfigDeclaration,
    DeliverableType,
    DispatchEnvelope,
    ExemptionReason,
    GateOutcome,
    Marker,
    ResolvedType,
    RootMarker,
    StepIdPresence,
)


# The ``scenarios(...)`` binding lives in the package-root ``test_*.py`` runner
# modules (collected by pytest); this module is the shared step-definition
# vocabulary, imported by ``conftest`` so every binding resolves it. Mirrors the
# ``activation_gating`` precedent.


# ---------------------------------------------------------------------------
# Parser converters -- coerce Gherkin literals to typed enums (DSL emergence).
# Each enum is matched by NAME (the feature files quote the enum member name,
# e.g. "PLUGIN", "NESTED_NWAVE_SKILLS") so a single typed decorator covers the
# whole literal space -- the DSL emerges from the type system (Mandate-12).
# ---------------------------------------------------------------------------

_ENUM_TOKEN = r"[A-Za-z0-9_-]+"


def _by_name(enum_cls):
    """Build a ``parse`` converter that maps an enum member NAME to the member."""

    def convert(text: str):
        return enum_cls[text]

    convert.pattern = _ENUM_TOKEN
    convert.__name__ = f"convert_{enum_cls.__name__}"
    return convert


EXTRA_TYPES = {
    "DeliverableType": _by_name(DeliverableType),
    "ConfigDeclaration": _by_name(ConfigDeclaration),
    "RootMarker": _by_name(RootMarker),
    "ResolvedType": _by_name(ResolvedType),
}


# ===========================================================================
# GIVEN -- preconditions (typed in; on-disk / in-memory INPUT state out)
# ===========================================================================


@given(
    parsers.parse(
        'a project that builds a "{deliverable:DeliverableType}" deliverable',
        extra_types=EXTRA_TYPES,
    ),
)
def Given_deliverable_type(composition, deliverable: DeliverableType) -> None:
    composition.recorded["deliverable"] = deliverable


@given(
    parsers.parse(
        'a project that builds an "{deliverable:DeliverableType}" deliverable',
        extra_types=EXTRA_TYPES,
    ),
)
def Given_deliverable_type_an(composition, deliverable: DeliverableType) -> None:
    composition.recorded["deliverable"] = deliverable


@given(
    parsers.parse(
        'the project declares its deliverable type as "{declaration:ConfigDeclaration}"',
        extra_types=EXTRA_TYPES,
    ),
)
def Given_config_declaration(composition, declaration: ConfigDeclaration) -> None:
    composition.given_config_declaration(declaration)


@given(
    parsers.parse(
        'the project has a "{marker:RootMarker}" at its root', extra_types=EXTRA_TYPES
    ),
)
def Given_root_marker(composition, marker: RootMarker) -> None:
    composition.given_root_marker(marker)


# ===========================================================================
# WHEN -- single user action / system event (drive real production code)
# ===========================================================================


@when("an agent is dispatched to run a planned step with no markers")
def When_dispatch_planned_step(composition) -> None:
    composition.dispatch(
        DispatchEnvelope(
            step_id=StepIdPresence.HAS_STEP_ID,
            marker=Marker.NONE,
            deliverable=composition.recorded["deliverable"],
        )
    )


@when("an agent is dispatched to run a planned step carrying an explicit exemption")
def When_dispatch_planned_step_exempt(composition) -> None:
    composition.dispatch(
        DispatchEnvelope(
            step_id=StepIdPresence.HAS_STEP_ID,
            marker=Marker.ENFORCEMENT_EXEMPT,
            deliverable=composition.recorded["deliverable"],
        )
    )


@when("an agent is dispatched with an ordinary request and no planned step")
def When_dispatch_ordinary(composition) -> None:
    composition.dispatch(
        DispatchEnvelope(
            step_id=StepIdPresence.NO_STEP_ID,
            marker=Marker.NONE,
            deliverable=composition.recorded["deliverable"],
        )
    )


@given("a project on disk that declares it builds a plugin")
def Given_plugin_project_on_disk(composition) -> None:
    composition.given_config_declaration(ConfigDeclaration.PROJECT_PLUGIN)


@when("the hook fires for a planned step with no markers")
def When_hook_fires_planned_step(composition) -> None:
    composition.dispatch_via_handler(
        DispatchEnvelope(
            step_id=StepIdPresence.HAS_STEP_ID,
            marker=Marker.NONE,
            deliverable=DeliverableType.PLUGIN,
        )
    )


@when("the deliverable type is resolved for this project")
def When_resolve_config(composition) -> None:
    composition.resolve_config_type()


@when("the deliverable type is detected from the project tree")
def When_detect(composition) -> None:
    composition.detect_root_type()


# ===========================================================================
# THEN -- observable outcomes (port-exposed; single captured observable)
# ===========================================================================


@then("the dispatch is allowed to proceed")
def Then_allowed(composition) -> None:
    assert composition.last_gate_outcome is GateOutcome.EXEMPT


@then("the dispatch is blocked for missing discipline markers")
def Then_blocked(composition) -> None:
    assert composition.last_gate_outcome is GateOutcome.BLOCKED


@then("it is waved through because of the deliverable type")
def Then_exempt_by_type(composition) -> None:
    assert composition.last_exemption_reason is ExemptionReason.TYPE_CARRIED


@then("it is waved through because of the explicit marker")
def Then_exempt_by_marker(composition) -> None:
    assert composition.last_exemption_reason is ExemptionReason.EXPLICIT_MARKER


@then("it is waved through because there was no planned step")
def Then_exempt_no_step(composition) -> None:
    assert composition.last_exemption_reason is ExemptionReason.NO_STEP_ID


@then("no per-dispatch exemption marker was needed")
def Then_no_marker_needed(composition) -> None:
    assert composition.last_decision_carries_exempt_marker is False


@then(
    parsers.parse(
        'the resolved deliverable type is "{expected:ResolvedType}"',
        extra_types=EXTRA_TYPES,
    ),
)
def Then_resolved_is(composition, expected: ResolvedType) -> None:
    # State-delta over the FULL port-exposed universe (Mandate 8 / D1
    # @contract-shape:unbounded-preservation): resolution is a PURE read, so the
    # ONLY slot that may change is ``config.resolved_type``; every other slot --
    # both on-disk config texts AND the whole root FS-tree hash -- must be
    # byte-identical. ``strict=True`` forbids any hidden mutation on an adjacent
    # slot, which is what proves a mis-spelled declaration is not silently
    # rescued by (nor allowed to synthesise) a root ``skills/`` folder.
    after = composition.capture_universe()
    assert_state_delta(
        composition.before_universe,
        after,
        universe=set(after.keys()),
        expected={"config.resolved_type": set_to(expected)},
        strict=True,
    )
    assert composition.last_resolved_type is expected


@then(
    parsers.parse(
        'the detected deliverable type is "{expected:ResolvedType}"',
        extra_types=EXTRA_TYPES,
    ),
)
def Then_detected_is(composition, expected: ResolvedType) -> None:
    assert composition.last_detected_type is expected
