"""Binding — pre-commit + pre-push gates (layer 3, real git in tmp repo).

The pre-commit + pre-push slices have landed: these scenarios run against the
real hook entries (nothing is skipped). Shared Tier-A step vocabulary via
``import *`` (Mandate-12 single vocabulary).
"""

from pytest_bdd import scenarios

from tests.des.acceptance.commit_author_identity.steps.steps_commit_author_identity import *  # noqa: F403


scenarios("local-identity-gates.feature")
