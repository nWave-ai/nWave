"""
Pytest-BDD Configuration and Fixtures for Manifest Circular Dependency Bug Tests.

This module provides shared fixtures for testing the installer bug where
manifest creation has a circular dependency with validation.
"""

import logging
from pathlib import Path

import pytest


# -----------------------------------------------------------------------------
# Fixtures: Test Environment
# -----------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Return the ai-craft project root directory."""
    # Navigate from tests/bugs/installer/manifest-circular-dependency/acceptance/steps/ to project root
    current = Path(__file__).resolve()
    return current.parents[6]  # 6 levels up from conftest.py


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.installer-manifest-bug")
    logger.setLevel(logging.DEBUG)

    # Add console handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
