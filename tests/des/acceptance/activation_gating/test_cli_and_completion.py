"""CLI + completion binding — project-activation-gating (DISTILL scaffold).

CLI verbs (enable/disable/mode/status), bad-args usage error, shell completion
no-drift + no-"hooks", and silent backward-compat migration. SKIPPED until
DELIVER.
"""

from pytest_bdd import scenarios

from tests.des.acceptance.activation_gating.steps.steps_activation_gating import *  # noqa: F403


scenarios("cli-and-completion.feature")
