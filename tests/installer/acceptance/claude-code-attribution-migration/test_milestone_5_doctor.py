"""Binder — doctor attribution report (AC9)."""

from pytest_bdd import scenario


@scenario(
    "milestone-5-doctor.feature",
    "Diagnosis reports current credit owner, legacy hook, and deprecated toggle",
)
def test_doctor_attribution_report():
    """AC9 — doctor surfaces 3-line attribution report via run_doctor."""
