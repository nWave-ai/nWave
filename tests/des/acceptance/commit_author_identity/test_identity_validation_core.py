"""Binding — validator-core scenarios (layer 1/2, pure driving-port call).

The validator-core slice has landed: these scenarios run against the real
validator (nothing is skipped). The shared Tier-A step vocabulary is pulled in
via ``import *`` (Mandate-12 single vocabulary).
"""

from pytest_bdd import scenarios

from tests.des.acceptance.commit_author_identity.steps.steps_commit_author_identity import *  # noqa: F403


scenarios("identity-validation-core.feature")
