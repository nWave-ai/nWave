"""Pytest-bdd configuration for installer silent-verifier regression scenarios.

@failing-tagged scenarios are auto-marked ``xfail`` until step 01-02 deploys
the M1 + M2 fixes (content-aware verifier + skills-filter diagnostic log).
The xfail is *operational*, not contractual — the scenarios still raise the
real ``AssertionError`` proving the bug is present pre-fix. The CI signal
flips XFAIL→XPASS the moment the fix lands; ``strict=False`` keeps the suite
green during the transition, after which the xfail marker can be lifted.

Mirror of the established pattern under
``tests/bugs/plugins/des/installation/acceptance/conftest.py``.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used by the regression feature file."""
    config.addinivalue_line(
        "markers",
        "bug-installer-silent-verifier: Bug — installer reports green while disk state diverges",
    )
    config.addinivalue_line(
        "markers",
        "rca-root-cause-A: Root Cause A — verifier existence-only check (install_nwave.py:608)",
    )
    config.addinivalue_line(
        "markers",
        "rca-root-cause-B: Root Cause B — filter_public_skills silent drop (skills_plugin.py:217)",
    )
    config.addinivalue_line(
        "markers",
        "bug-pytest-build-tier-timeouts: Bug — build-tier subprocess timeouts under-budgeted vs parallel contention",
    )
    config.addinivalue_line(
        "markers",
        "bug-roadmap-schema-drift: Bug — roadmap.json skeleton/validator drift from schema source-of-truth",
    )
    config.addinivalue_line(
        "markers",
        "property-test: scenario expresses a system property (PBT framing)",
    )
    config.addinivalue_line(
        "markers",
        "driving_port: scenario enters production through a public driving port",
    )
    config.addinivalue_line(
        "markers",
        "failing: Expected to fail until the fix is deployed (xfail strict=False)",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark scenarios tagged ``@failing`` as ``xfail`` (non-strict)."""
    for item in items:
        for marker in item.iter_markers():
            if marker.name == "failing":
                item.add_marker(
                    pytest.mark.xfail(
                        reason=(
                            "RED phase: bug present pre-fix. Flips to XPASS "
                            "when step 01-02 ships M1 + M2 (content-aware "
                            "verifier + skills-filter diagnostic)."
                        ),
                        strict=False,
                    )
                )
                break
