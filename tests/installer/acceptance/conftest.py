"""
Pytest configuration for DES acceptance tests.

Provides shared fixtures for test setup and teardown.
"""

import pytest


@pytest.fixture
def in_memory_filesystem():
    """
    In-memory filesystem for testing without disk I/O.

    Returns:
        InMemoryFileSystem: Fresh in-memory filesystem instance
    """
    from tests.des.adapters import InMemoryFileSystem

    return InMemoryFileSystem()


@pytest.fixture
def mocked_time_provider():
    """
    Mocked time provider with fixed time for deterministic testing.

    Returns:
        MockedTimeProvider: Time provider starting at 2026-01-26T10:00:00Z
    """
    from datetime import datetime, timezone

    from tests.des.adapters import MockedTimeProvider

    return MockedTimeProvider(datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def mocked_hook():
    """
    Mocked subagent stop hook for testing without real hook behavior.

    Returns:
        MockedSubagentStopHook: Hook that returns predefined results
    """
    from tests.des.adapters import MockedSubagentStopHook

    return MockedSubagentStopHook()


@pytest.fixture
def mocked_validator():
    """
    Mocked template validator for testing without real validation.

    Returns:
        MockedTemplateValidator: Validator returning passing results by default
    """
    from tests.des.adapters import MockedTemplateValidator

    return MockedTemplateValidator()


@pytest.fixture
def des_orchestrator(
    in_memory_filesystem, mocked_hook, mocked_validator, mocked_time_provider
):
    """
    DES orchestrator with mocked adapters for testing.

    Uses in-memory filesystem and mocked time/hook/validator for:
    - Zero real filesystem operations
    - Deterministic time behavior
    - Fast test execution (<1 second)

    Returns:
        DESOrchestrator: Configured orchestrator with mocked dependencies
    """
    from des.application.orchestrator import DESOrchestrator

    return DESOrchestrator(
        hook=mocked_hook,
        validator=mocked_validator,
        filesystem=in_memory_filesystem,
        time_provider=mocked_time_provider,
    )


@pytest.fixture
def tmp_project_root(tmp_path):
    """
    Temporary project root directory for acceptance tests.

    Provides a clean temporary directory for each test to create step files,
    logs, and other temporary artifacts without affecting the real filesystem.

    Returns:
        pathlib.Path: Temporary directory path for test use
    """
    return tmp_path


@pytest.fixture
def minimal_step_file(tmp_project_root):
    """
    Temporary step file for testing hook validation.

    Provides a Path object pointing to a temporary JSON step file in the
    test project root. Tests can write step data to this file and validate
    hook behavior against it.

    Returns:
        pathlib.Path: Path to temporary step.json file
    """
    step_file = tmp_project_root / "step.json"
    return step_file
