"""Register BDD tags used by the pi-harness walking skeleton as markers."""

from __future__ import annotations


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "walking_skeleton: Walking skeleton tests")
    config.addinivalue_line(
        "markers", "driving_port: Driving-port (entry-point) acceptance tests"
    )
