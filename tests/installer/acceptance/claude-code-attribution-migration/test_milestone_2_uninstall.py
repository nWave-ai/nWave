"""Binder — uninstall surgical removal + user-modified preservation (AC4, AC5)."""

from pytest_bdd import scenario


@scenario(
    "milestone-2-uninstall.feature",
    "Uninstall removes the nWave credit and keeps unrelated preferences",
)
def test_uninstall_surgical():
    """AC4 — uninstall removes only nWave's credit, keeps neighbours."""


@scenario(
    "milestone-2-uninstall.feature",
    "Uninstall leaves a credit the developer edited after install untouched",
)
def test_uninstall_preserves_user_modified():
    """AC5 — uninstall preserves a credit edited after install."""
