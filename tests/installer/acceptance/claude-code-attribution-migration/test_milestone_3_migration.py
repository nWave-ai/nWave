"""Binder — legacy-hook migration (AC6)."""

from pytest_bdd import scenario


@scenario(
    "milestone-3-migration.feature",
    "Installing over a legacy hook retires it and adopts the dual credit",
)
def test_migration_retires_legacy_hook():
    """AC6 — migration dismantles the legacy hook and adopts the dual credit."""
