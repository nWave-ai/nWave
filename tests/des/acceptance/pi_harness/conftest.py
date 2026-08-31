"""Register BDD tags used by the pi-harness walking skeleton as markers."""

from __future__ import annotations


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "walking_skeleton: Walking skeleton tests")
    config.addinivalue_line(
        "markers", "driving_port: Driving-port (entry-point) acceptance tests"
    )
    # pytest-bdd registers Gherkin tags verbatim (hyphens preserved). Register
    # the exact tag strings the .feature files use, under --strict-markers.
    for marker, desc in (
        ("real-io", "Scenarios exercising real adapters with real I/O"),
        ("adapter-integration", "Adapter integration scenarios (real I/O at the seam)"),
        ("error", "Error / sad-path scenarios"),
        ("US-1", "Story 1 (install + crafter available)"),
        ("US-2", "Story 2 (RED gate)"),
        ("US-3", "Story 3 (GREEN / refactor / no-regression)"),
        ("requires_external", "Needs a live pi model backend; skipped by default"),
    ):
        config.addinivalue_line("markers", f"{marker}: {desc}")
