"""Gitignore-tracking binding — project-activation-gating (DISTILL scaffold).

Dual-layer gitignore fix: the marker becomes git-trackable, the banner is
preserved, the fix is idempotent, and every root-ignore line variant is
handled. SKIPPED until DELIVER.
"""

from pytest_bdd import scenarios

from tests.des.acceptance.activation_gating.steps.steps_activation_gating import *  # noqa: F403


scenarios("gitignore-tracking.feature")
