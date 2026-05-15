"""Conftest for tests/state_delta/ — auto-marks by sub-directory tier."""

from __future__ import annotations

import pytest


_TIER_MAP: dict[str, str] = {
    "tests/state_delta/unit/": "unit",
    "tests/state_delta/integration/": "integration",
    "tests/state_delta/chaos/": "integration",  # chaos tests use real I/O — integration tier
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark state_delta tests with tier markers based on directory path."""
    for item in items:
        node_path = str(item.fspath).replace("\\", "/")
        # Find the longest matching prefix (most specific wins).
        matched_tier: str | None = None
        matched_len = 0
        for prefix, tier in _TIER_MAP.items():
            if prefix in node_path and len(prefix) > matched_len:
                matched_tier = tier
                matched_len = len(prefix)
        if matched_tier is not None:
            item.add_marker(getattr(pytest.mark, matched_tier))
