"""Binder — attribution CLI on/off/status (AC7)."""

from pytest_bdd import scenario


@scenario(
    "milestone-4-cli.feature",
    "Turning attribution on applies the dual credit",
)
def test_cli_on():
    """AC7 (ADR-CA-007) — `attribution on` registers the hook without writing
    the settings credit. 01-02 removed the retired CLI `on` settings-write, so
    the no-settings-credit observable now holds."""


@scenario(
    "milestone-4-cli.feature",
    "Turning attribution off removes the credit",
)
def test_cli_off():
    """AC7 — `attribution off` removes the credit (routes to settings.json)."""
