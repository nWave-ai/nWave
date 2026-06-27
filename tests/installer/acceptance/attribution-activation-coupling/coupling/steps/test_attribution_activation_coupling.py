"""Scenario bindings — attribution-activation-coupling (DISTILL scaffold).

Binds all five `.feature` files (one walking skeleton + four milestones) to the
shared Tier-A step vocabulary in `steps_attribution.py`. The composition root and
all business logic live in `composition.py` (Pillar 3 / Mandate-12 SSOT).

Skip policy (one-at-a-time, ADR-025): the walking-skeleton scenario carries NO
`@skip` tag and therefore RUNS — it is the pre-DELIVER fail-for-right-reason
entry point and must fail RED (MISSING_FUNCTIONALITY), never be skipped. Every
milestone scenario carries `@skip`, translated to `pytest.mark.skip` by the
`pytest_bdd_apply_tag` hook in `conftest.py`; DELIVER unskips them one at a time.

Example-only, no PBT machinery (Mandate 9/11): this is a config-shaped install /
CLI / doctor slice over finite enumerable states (3 activation postures x 3
preferences x 3 settings-availability shapes), so every materially-distinct case
is enumerated as a `Scenario:`. Sad paths (AB-2/AB-3/AB-5/AB-11) are named
example scenarios, never generated.
"""

from pytest_bdd import scenarios

# Pull the shared Tier-A step vocabulary into this module's namespace so
# pytest-bdd resolves every Given/When/Then.
from .steps_attribution import *  # noqa: F403


scenarios(
    "../walking-skeleton.feature",
    "../milestone-1-trailer-scope.feature",
    "../milestone-2-upgrade-migration.feature",
    "../milestone-3-cli-toggle.feature",
    "../milestone-4-doctor-report.feature",
)
