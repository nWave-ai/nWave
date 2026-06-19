"""Hook-gate binding — project-activation-gating (DISTILL scaffold).

Gate behaviour: inactive → allow/exit-0 (never block); active → dispatch;
SessionStart exempt; stdin re-injected intact. SKIPPED until DELIVER.
"""

from pytest_bdd import scenarios

from tests.des.acceptance.activation_gating.steps.steps_activation_gating import *  # noqa: F403


scenarios("hook-gate.feature")
