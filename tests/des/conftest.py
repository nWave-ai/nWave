"""
Pytest configuration for DES unit tests.

Provides shared fixtures with mocked adapters for deterministic testing.
"""

import pytest


# =============================================================================
# TDD Schema Fixtures (Single Source of Truth)
# =============================================================================


@pytest.fixture(scope="session")
def tdd_schema():
    """
    TDD schema loaded from step-tdd-cycle-schema.json.

    This is the SINGLE SOURCE OF TRUTH for all TDD-related test data.
    No hardcoded phase names or statuses in tests - use this fixture.

    Returns:
        TDDSchema: Immutable schema data container with:
            - tdd_phases: Ordered tuple of phase names
            - valid_statuses: Valid phase execution statuses
            - valid_skip_prefixes: Skip prefixes that allow commit
            - blocking_skip_prefixes: Skip prefixes that block commit
    """
    from des.domain.tdd_schema import get_tdd_schema

    return get_tdd_schema()


@pytest.fixture(scope="session")
def tdd_phases(tdd_schema):
    """
    List of TDD phase names from schema for parametrized tests.

    Usage:
        @pytest.mark.parametrize("phase", tdd_phases)
        def test_something_with_phase(phase):
            ...

    Returns:
        tuple[str, ...]: ('PREPARE', 'RED_ACCEPTANCE', ..., 'COMMIT')
    """
    return tdd_schema.tdd_phases


@pytest.fixture(scope="session")
def valid_skip_prefixes(tdd_schema):
    """
    Skip prefixes that allow commit, from schema.

    Returns:
        tuple[str, ...]: ('BLOCKED_BY_DEPENDENCY:', 'NOT_APPLICABLE:', ...)
    """
    return tdd_schema.valid_skip_prefixes


@pytest.fixture(scope="session")
def blocking_skip_prefixes(tdd_schema):
    """
    Skip prefixes that block commit, from schema.

    Returns:
        tuple[str, ...]: ('DEFERRED:', ...)
    """
    return tdd_schema.blocking_skip_prefixes


@pytest.fixture(scope="session")
def valid_statuses(tdd_schema):
    """
    Valid phase execution statuses from schema.

    Returns:
        tuple[str, ...]: ('NOT_EXECUTED', 'IN_PROGRESS', 'EXECUTED', 'SKIPPED')
    """
    return tdd_schema.valid_statuses


# =============================================================================
# Prompt Template Fixtures
# =============================================================================


@pytest.fixture
def valid_prompt_v3(tdd_phases):
    """
    Generate valid DES prompt with all mandatory sections from template.

    Uses canonical phase names from schema (single source of truth).
    Prompt adapts automatically if template changes.

    Args:
        tdd_phases: Phase names from schema fixture

    Returns:
        Callable that generates valid prompt, optionally excluding sections for error testing.

    Usage:
        # Complete valid prompt
        prompt = valid_prompt_v3()

        # Prompt missing TIMEOUT_INSTRUCTION (for testing validation errors)
        prompt = valid_prompt_v3(exclude_sections=['TIMEOUT_INSTRUCTION'])
    """

    def _generate(exclude_sections=None):
        if exclude_sections is None:
            exclude_sections = []

        # Load phases from schema (automatic sync with template)
        phases_text = ", ".join(tdd_phases)

        sections = {
            "DES_VALIDATION_MARKER": "<!-- DES-VALIDATION: required -->",
            "DES_METADATA": """## DES_METADATA
step_id: test-01-01
project_id: test-project
step_file: steps/test-01-01.json""",
            "AGENT_IDENTITY": """## AGENT_IDENTITY
You are @software-crafter executing this step.""",
            "TASK_CONTEXT": """## TASK_CONTEXT
Implement test feature with complete TDD cycle.""",
            "TDD_PHASES": f"""## TDD_PHASES
Execute all {len(tdd_phases)} phases from schema:
{phases_text}""",
            "QUALITY_GATES": """## QUALITY_GATES
G1: All tests pass
G2: No code smells
G3: Coverage >= 80%
G4: No security vulnerabilities
G5: Documentation complete
G6: Commit message descriptive""",
            "OUTCOME_RECORDING": """## OUTCOME_RECORDING
Record phase outcomes in step file:
- EXECUTED phases: record outcome (PASS/FAIL)
- SKIPPED phases: record reason with valid prefix
- Update phase_execution_log after each phase""",
            "RECORDING_INTEGRITY": """## RECORDING_INTEGRITY
Valid Skip Prefixes: NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
Anti-Fraud Rules: NEVER write EXECUTED for phases not actually performed.
NEVER invent timestamps. DES audits all entries.""",
            "BOUNDARY_RULES": """## BOUNDARY_RULES
ALLOWED:
- Modify implementation files in scope
- Create/modify test files
- Update step file metadata

FORBIDDEN:
- Modify files outside scope
- Skip mandatory phases without valid reason
- Commit without all phases complete""",
            "TIMEOUT_INSTRUCTION": """## TIMEOUT_INSTRUCTION
Turn budget: approximately 50 turns
Progress checkpoints: ~10, ~25, ~40, ~50
Early exit protocol: Save progress if stuck
Turn logging: Log turn count at phase transitions""",
        }

        # Build prompt with only non-excluded sections
        prompt_parts = []
        for section_name, section_content in sections.items():
            if section_name not in exclude_sections:
                prompt_parts.append(section_content)

        return "\n\n".join(prompt_parts)

    return _generate


@pytest.fixture
def prompt_missing_phase_v3(tdd_phases):
    """
    Generate DES prompt with one TDD phase missing for error testing.

    Uses canonical phase names from schema (single source of truth).

    Args:
        tdd_phases: Phase names from schema fixture

    Returns:
        Callable that generates prompt missing specified phase.

    Usage:
        # Prompt missing REFACTOR_CONTINUOUS phase
        prompt = prompt_missing_phase_v3(missing_phase='REFACTOR_CONTINUOUS')
    """

    def _generate(missing_phase):
        # Filter out the missing phase
        phases_with_missing = [p for p in tdd_phases if p != missing_phase]
        phases_text = ", ".join(phases_with_missing)

        return f"""<!-- DES-VALIDATION: required -->

## DES_METADATA
step_id: test-01-01
project_id: test-project
step_file: steps/test-01-01.json

## AGENT_IDENTITY
You are @software-crafter executing this step.

## TASK_CONTEXT
Implement test feature with complete TDD cycle.

## TDD_PHASES
Execute all {len(tdd_phases)} phases from schema:
{phases_text}

## QUALITY_GATES
G1: All tests pass
G2: No code smells
G3: Coverage >= 80%
G4: No security vulnerabilities
G5: Documentation complete
G6: Commit message descriptive

## OUTCOME_RECORDING
Record phase outcomes in step file:
- EXECUTED phases: record outcome (PASS/FAIL)
- SKIPPED phases: record reason with valid prefix
- Update phase_execution_log after each phase

## RECORDING_INTEGRITY
Valid Skip Prefixes: NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
Anti-Fraud Rules: NEVER write EXECUTED for phases not actually performed.
NEVER invent timestamps. DES audits all entries.

## BOUNDARY_RULES
ALLOWED:
- Modify implementation files in scope
- Create/modify test files
- Update step file metadata

FORBIDDEN:
- Modify files outside scope
- Skip mandatory phases without valid reason
- Commit without all phases complete

## TIMEOUT_INSTRUCTION
Turn budget: approximately 50 turns
Progress checkpoints: ~10, ~25, ~40, ~50
Early exit protocol: Save progress if stuck
Turn logging: Log turn count at phase transitions"""

    return _generate


# =============================================================================
# Filesystem Fixtures
# =============================================================================


@pytest.fixture
def in_memory_filesystem():
    """
    In-memory filesystem for testing without disk I/O.

    Returns:
        InMemoryFileSystem: Fresh in-memory filesystem instance
    """
    from des.adapters.driven.filesystem.in_memory_filesystem import (
        InMemoryFileSystem,
    )

    return InMemoryFileSystem()


@pytest.fixture
def mocked_time_provider():
    """
    Mocked time provider with fixed time for deterministic testing.

    Returns:
        MockedTimeProvider: Time provider starting at 2026-01-26T10:00:00Z
    """
    from datetime import datetime, timezone

    from des.adapters.driven.time.mocked_time import MockedTimeProvider

    return MockedTimeProvider(datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def mocked_hook():
    """
    Mocked subagent stop hook for testing without real hook behavior.

    Returns:
        MockedSubagentStopHook: Hook that returns predefined results
    """
    from des.adapters.drivers.hooks.mocked_hook import MockedSubagentStopHook

    return MockedSubagentStopHook()


@pytest.fixture
def mocked_validator():
    """
    Mocked template validator for testing without real validation.

    Returns:
        MockedTemplateValidator: Validator returning passing results by default
    """
    from des.adapters.drivers.validators.mocked_validator import (
        MockedTemplateValidator,
    )

    return MockedTemplateValidator()


@pytest.fixture
def tmp_project_root(tmp_path):
    """
    Temporary project root directory for acceptance and e2e tests.

    Provides a clean temporary directory for each test to create step files,
    logs, and other temporary artifacts without affecting the real filesystem.

    Returns:
        Path: Temporary directory path
    """
    return tmp_path


@pytest.fixture
def minimal_step_file(tmp_project_root):
    """
    Temporary step file for testing hook validation.

    Creates a minimal JSON step file in the test project root with basic
    step data. Tests can read this file or override its contents.

    Returns:
        pathlib.Path: Path to temporary step.json file with minimal content
    """
    import json

    step_file = tmp_project_root / "step.json"
    minimal_step_data = {
        "id": "01-01",
        "phase": "RED",
        "status": "pending",
        "description": "Test step for DES validation",
        "scope": {
            "files": ["src/test_module.py"],
            "test_files": ["tests/test_module.py"],
        },
    }
    step_file.write_text(json.dumps(minimal_step_data, indent=2))
    return step_file


@pytest.fixture
def des_orchestrator(
    in_memory_filesystem, mocked_hook, mocked_validator, mocked_time_provider
):
    """
    DES orchestrator with all mocked adapters for unit testing.

    Uses in-memory filesystem, mocked time, mocked hook, and mocked validator for:
    - Zero real filesystem operations
    - Deterministic time behavior
    - Fast test execution (<1 second)
    - Predictable validation results

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
def scenario_des_orchestrator(mocked_hook, mocked_validator, mocked_time_provider):
    """
    DES orchestrator for E2E scenario testing.

    Uses real filesystem for E2E tests (unlike unit tests) to support
    tempfile-based test scenarios. Still uses mocked time, hook, and validator
    for deterministic behavior.

    Returns:
        DESOrchestrator: Configured orchestrator with real filesystem
    """
    from des.adapters.driven.filesystem.real_filesystem import RealFileSystem
    from des.application.orchestrator import DESOrchestrator

    return DESOrchestrator(
        hook=mocked_hook,
        validator=mocked_validator,
        filesystem=RealFileSystem(),
        time_provider=mocked_time_provider,
    )
