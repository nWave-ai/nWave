"""InMemoryComposition for Tier-B state-machine exploration (Mandate 10 / Pillar 3).

Same interface contract as the production ``ActivationGatingComposition`` but
wired with an in-memory marker/mode model — no filesystem, no subprocess. This
is layer 1-2 (in-memory acceptance), so PBT-full is permitted here (Mandate 9)
while the Tier-A ``.feature`` suite at layer 3 stays example-only.

The model: a project's marker is one of {absent, enabled, disabled}; a global
mode is one of {opt-in, all}. Adoption writes the marker ONLY when it is absent
(adoption is always warranted in this model — the Tier-A suite covers the
evidence predicate); it is a no-op when the marker is present in either
direction (sticky). ``resolve`` mirrors the ADR-AG-002 truth table via the SAME
production ``resolve_activation`` policy, so the two tiers cannot drift on the
resolution rule. ``capture_universe`` returns the port-exposed snapshot consumed
by ``assert_state_delta``.
"""

from __future__ import annotations

from des.domain.activation_policy import resolve_activation
from tests.des.acceptance.activation_gating.steps.domain_types import (
    Activation,
    AdoptionTrigger,
    GlobalMode,
    MarkerState,
)


class InMemoryComposition:
    """In-memory double honoring the activation-gating service contract."""

    def __init__(self) -> None:
        self._mode: GlobalMode = GlobalMode.OPT_IN
        self._marker: MarkerState = MarkerState.ABSENT

    def given_global_mode(self, mode: GlobalMode) -> None:
        self._mode = mode

    def given_marker(self, marker: MarkerState) -> None:
        self._marker = marker

    def adopt(self, trigger: AdoptionTrigger) -> None:
        """Adoption writes the marker only when absent; never over a present one."""
        if self._marker is MarkerState.ABSENT:
            self._marker = MarkerState.ENABLED

    def enable(self) -> None:
        self._marker = MarkerState.ENABLED

    def disable(self) -> None:
        self._marker = MarkerState.DISABLED

    def resolve(self) -> Activation:
        verdict = resolve_activation(self._marker_enabled(), self._mode_value())
        return Activation.ACTIVE if verdict else Activation.INACTIVE

    def capture_universe(self) -> dict[str, object]:
        return {"marker.enabled_for_repo": self._marker_enabled()}

    # ---- model helpers ----

    def _marker_enabled(self) -> bool | None:
        if self._marker is MarkerState.ENABLED:
            return True
        if self._marker is MarkerState.DISABLED:
            return False
        return None

    def _mode_value(self) -> str | None:
        if self._mode in (GlobalMode.ABSENT, GlobalMode.CORRUPT):
            return None
        return self._mode.value
