"""
Bug 2: Audit Logs Location - Acceptance Tests.

Tests that verify:
- Default location is project-local .nwave/des/logs/
- Logs do NOT go to global ~/.claude/des/logs/
- Location is configurable via DES_AUDIT_LOG_DIR environment variable
- Location is configurable via config file
- Project isolation of audit trails
"""

from pytest_bdd import scenarios

from .steps.audit_log_steps import *  # noqa: F403

# Import step definitions - must use star imports for pytest-bdd registration
from .steps.common_steps import *  # noqa: F403


# Collect all scenarios from the feature file
scenarios("bug-2-audit-logs-location.feature")
