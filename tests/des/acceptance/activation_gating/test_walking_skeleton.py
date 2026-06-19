"""Walking-skeleton binding — project-activation-gating (DISTILL scaffold).

One demo-able end-to-end journey through the production composition root: a
developer activates a project, the marker is written and made trackable, the
banner is preserved. Tagged @walking_skeleton @driving_port @real-io.

SKIPPED at the module level so the suite stays green now; DELIVER removes the
skip first (it is the one-at-a-time entry point) and implements until GREEN.
"""

from pytest_bdd import scenarios

# Pull the shared Tier-A step vocabulary into this module's namespace.
from tests.des.acceptance.activation_gating.steps.steps_activation_gating import *  # noqa: F403


scenarios("walking-skeleton.feature")
