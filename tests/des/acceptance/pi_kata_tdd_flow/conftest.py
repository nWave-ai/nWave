"""Register BDD tags used by the pi-kata-tdd-flow acceptance suite as markers."""

from __future__ import annotations


def pytest_configure(config) -> None:
    for marker, desc in (
        ("walking_skeleton", "Walking skeleton tests (inherited from pi-harness)"),
        ("driving_port", "Driving-port (entry-point) acceptance tests"),
        ("real-io", "Scenarios exercising real adapters with real I/O"),
        ("adapter-integration", "Adapter integration scenarios (real I/O at the seam)"),
        ("in-memory", "Scenarios using in-memory doubles"),
        ("error", "Error / sad-path scenarios"),
        ("US-1", "Story 1 (self-bootstrap a DES-tracked kata session)"),
        ("US-2", "Story 2 (self-driven per-test cycle with phase recording)"),
        ("US-3", "Story 3 (solve a kata end-to-end, strictly verified)"),
        ("requires_external", "Needs a live pi model backend; skipped by default"),
        # pytest-bdd registers the full Gherkin tag verbatim, including the value
        # after the colon (2026-05-15 contract-shape mandate). Register each.
        ("contract-shape:pure-function", "Contract shape: pure function"),
        ("contract-shape:bounded-change", "Contract shape: bounded change"),
        (
            "contract-shape:unbounded-preservation",
            "Contract shape: unbounded preservation",
        ),
    ):
        config.addinivalue_line("markers", f"{marker}: {desc}")
