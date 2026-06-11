"""Milestone 1 bindings — core retention behavior (S1, S2, S3, S6)."""

from pytest_bdd import scenario


@scenario(
    "milestone-1-retention-core.feature",
    "Fresh install on a bare system creates no backup at all",
)
def test_s1_fresh_install_no_backup():
    pass


@scenario(
    "milestone-1-retention-core.feature",
    "Second install creates a second backup without pruning",
)
def test_s2_second_install_no_pruning():
    pass


@scenario(
    "milestone-1-retention-core.feature",
    "Eleventh install with default cap=10 prunes the oldest, foreign dirs untouched",
)
def test_s3_eleventh_install_prunes_oldest():
    pass


@scenario(
    "milestone-1-retention-core.feature",
    "Pool sums across install, uninstall, and update backup types",
)
def test_s6_pool_sums_across_types():
    pass
