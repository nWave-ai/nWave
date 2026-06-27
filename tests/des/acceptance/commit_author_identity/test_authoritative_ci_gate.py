"""Binding — authoritative CI runner + regression anchor (layer 3, real range).

The CI slice has landed: these scenarios run against the real
``ci_author_check`` runner (nothing is skipped). The ``@regression_anchor``
scenario encodes the real failing instance (PR #42, 8 commits authored
test@example.com) the feature exists to catch; the ``@error`` W1 scenarios drive
the runner over HEAD alone (no ``--base``), covering the degrade-to-HEAD path a
push event takes when no range exists. Shared Tier-A step vocabulary via
``import *`` (Mandate-12 single vocabulary).
"""

from pytest_bdd import scenarios

from tests.des.acceptance.commit_author_identity.steps.steps_commit_author_identity import *  # noqa: F403


scenarios("authoritative-ci-gate.feature")
