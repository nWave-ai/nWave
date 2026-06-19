"""Tier-B state-machine PBT — activation adoption journey (Mandate 10, DISTILL scaffold).

The auto-marking journey IS a state machine model (Hebert ch.11: model-shape-is-
state-machine): the marker moves through {absent, enabled, disabled} under the
commands {prior_use_adopt, agent_dispatch_adopt, cli_enable, cli_disable}, with
two safety invariants that example scenarios cannot exhaustively cover under
arbitrary command interleavings:

  INV-1 (sticky opt-out): once the marker is "disabled", NO adoption command
        ever flips it to enabled. A `disable` is permanent until an explicit
        `enable`.
  INV-2 (resolution agrees with marker): whenever the marker is present, the
        resolved activation equals the marker's direction regardless of mode.

This is layer 1-2 (in-memory doubles), so PBT-full is permitted (Mandate 9). It
runs against ``InMemoryComposition`` (same interface as the production root,
Pillar 3). Each ``@rule`` invokes the SAME service vocabulary as Tier A (shared
contract) — adopt / enable / disable — so the two tiers cannot drift.

SKIPPED at module level (DISTILL scaffold): both the in-memory composition and
the production services are RED. DELIVER implements them and unskips. Per Mandate
10 this Tier-B file is OPTIONAL but justified: the journey is ≥3 chained
commands and the sticky-opt-out invariant is exactly the kind of cross-command
safety property PBT is built to falsify.
"""

from __future__ import annotations

from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)
from hypothesis.strategies import sampled_from

from tests.des.acceptance.activation_gating.steps.domain_types import (
    Activation,
    AdoptionTrigger,
    GlobalMode,
    MarkerState,
)
from tests.des.acceptance.activation_gating.tier_b.in_memory_composition import (
    InMemoryComposition,
)


_TRIGGERS = sampled_from(list(AdoptionTrigger))


class ActivationAdoptionJourney(RuleBasedStateMachine):
    """Explore arbitrary interleavings of adopt / enable / disable commands."""

    @initialize()
    def setup(self) -> None:
        self.composition = InMemoryComposition()
        self.composition.given_global_mode(GlobalMode.OPT_IN)
        self.composition.given_marker(MarkerState.ABSENT)
        self._opted_out = False

    @rule(trigger=_TRIGGERS)
    def adopt(self, trigger: AdoptionTrigger) -> None:
        """Adoption writes the marker only when absent + warranted; never over sticky."""
        self.composition.adopt(trigger)

    @rule()
    def enable(self) -> None:
        self.composition.enable()
        self._opted_out = False

    @rule()
    def disable(self) -> None:
        self.composition.disable()
        self._opted_out = True

    @invariant()
    @precondition(lambda self: getattr(self, "_opted_out", False))
    def sticky_opt_out_is_never_flipped(self) -> None:
        """INV-1: after a disable, the marker is never silently re-enabled."""
        universe = self.composition.capture_universe()
        assert universe["marker.enabled_for_repo"] is False

    @invariant()
    def resolution_agrees_with_present_marker(self) -> None:
        """INV-2: a present marker dictates resolution in both directions."""
        universe = self.composition.capture_universe()
        marker = universe["marker.enabled_for_repo"]
        if marker is None:
            return
        expected = Activation.ACTIVE if marker else Activation.INACTIVE
        assert self.composition.resolve() is expected


TestActivationAdoptionJourney = ActivationAdoptionJourney.TestCase
