"""Auto-marking binding — project-activation-gating (DISTILL scaffold).

Two triggers (prior-use at session start; real agent dispatch), the
bare-config false-positive guard, the sticky opt-out, and the read-only
fail-open path. SKIPPED until DELIVER.
"""

from pytest_bdd import scenarios

from tests.des.acceptance.activation_gating.steps.steps_activation_gating import *  # noqa: F403


scenarios("auto-marking.feature")
