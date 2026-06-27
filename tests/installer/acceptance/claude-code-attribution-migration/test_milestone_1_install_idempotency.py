"""Binder — install idempotency + user-credit preservation (AC2, AC3)."""

from pytest_bdd import scenario


@scenario(
    "milestone-1-install-idempotency.feature",
    "Re-install retires a leftover nWave-applied credit",
)
def test_reinstall_retires_leftover_credit():
    """AC2 (ADR-CA-007) — re-install cleans up a leftover nWave-applied credit
    via migrate_legacy_settings_attribution (wired into install in 01-03);
    a user-modified value is preserved."""


@scenario(
    "milestone-1-install-idempotency.feature",
    "Re-install over a developer's own credit preserves it",
)
def test_reinstall_preserves_user_credit():
    """AC3 — re-install never overwrites a developer-authored credit. Under
    ADR-CA-007 install never touches the settings credit, so a user-authored
    value is trivially preserved (reconciled GREEN)."""
