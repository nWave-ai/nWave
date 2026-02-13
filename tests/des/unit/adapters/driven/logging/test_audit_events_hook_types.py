"""
Unit tests for HOOK audit event types.

Tests verify that 4 new HOOK event types exist in EventType enum:
- HOOK_PRE_TASK_PASSED
- HOOK_PRE_TASK_BLOCKED
- HOOK_SUBAGENT_STOP_PASSED
- HOOK_SUBAGENT_STOP_FAILED

Also verifies get_event_category() and validate_event_type() work correctly
for all new HOOK event types, and existing event types remain unchanged.
"""

import importlib.util
import sys


# Direct import from file to bypass broken __init__.py chain
spec = importlib.util.spec_from_file_location(
    "audit_events", "src/des/adapters/driven/logging/audit_events.py"
)
audit_events_module = importlib.util.module_from_spec(spec)
sys.modules["audit_events"] = audit_events_module
spec.loader.exec_module(audit_events_module)

EventType = audit_events_module.EventType
get_event_category = audit_events_module.get_event_category
validate_event_type = audit_events_module.validate_event_type


class TestHookEventTypesExist:
    """Test that all 4 HOOK event types exist in EventType enum."""

    def test_hook_pre_task_passed_exists(self):
        """HOOK_PRE_TASK_PASSED should exist in EventType enum."""
        assert hasattr(EventType, "HOOK_PRE_TASK_PASSED")
        assert EventType.HOOK_PRE_TASK_PASSED.value == "HOOK_PRE_TASK_PASSED"

    def test_hook_pre_task_blocked_exists(self):
        """HOOK_PRE_TASK_BLOCKED should exist in EventType enum."""
        assert hasattr(EventType, "HOOK_PRE_TASK_BLOCKED")
        assert EventType.HOOK_PRE_TASK_BLOCKED.value == "HOOK_PRE_TASK_BLOCKED"

    def test_hook_subagent_stop_passed_exists(self):
        """HOOK_SUBAGENT_STOP_PASSED should exist in EventType enum."""
        assert hasattr(EventType, "HOOK_SUBAGENT_STOP_PASSED")
        assert EventType.HOOK_SUBAGENT_STOP_PASSED.value == "HOOK_SUBAGENT_STOP_PASSED"

    def test_hook_subagent_stop_failed_exists(self):
        """HOOK_SUBAGENT_STOP_FAILED should exist in EventType enum."""
        assert hasattr(EventType, "HOOK_SUBAGENT_STOP_FAILED")
        assert EventType.HOOK_SUBAGENT_STOP_FAILED.value == "HOOK_SUBAGENT_STOP_FAILED"


class TestHookEventCategory:
    """Test that get_event_category() returns 'HOOK' for all 4 event types."""

    def test_get_event_category_returns_hook_for_all_four(self):
        """get_event_category() should return 'HOOK' for all 4 HOOK event types."""
        assert get_event_category("HOOK_PRE_TASK_PASSED") == "HOOK"
        assert get_event_category("HOOK_PRE_TASK_BLOCKED") == "HOOK"
        assert get_event_category("HOOK_SUBAGENT_STOP_PASSED") == "HOOK"
        assert get_event_category("HOOK_SUBAGENT_STOP_FAILED") == "HOOK"


class TestHookEventValidation:
    """Test that validate_event_type() accepts all 4 HOOK event types."""

    def test_validate_event_type_accepts_all_four(self):
        """validate_event_type() should accept all 4 HOOK event types."""
        assert validate_event_type("HOOK_PRE_TASK_PASSED") is True
        assert validate_event_type("HOOK_PRE_TASK_BLOCKED") is True
        assert validate_event_type("HOOK_SUBAGENT_STOP_PASSED") is True
        assert validate_event_type("HOOK_SUBAGENT_STOP_FAILED") is True


class TestExistingEventTypesUnchanged:
    """Test that existing event types remain valid (no regression)."""

    def test_existing_event_types_unchanged(self):
        """Existing event types should still be valid after adding HOOK types."""
        # TASK_INVOCATION events
        assert hasattr(EventType, "TASK_INVOCATION_STARTED")
        assert validate_event_type("TASK_INVOCATION_STARTED") is True
        assert get_event_category("TASK_INVOCATION_STARTED") == "TASK_INVOCATION"

        # PHASE events
        assert hasattr(EventType, "PHASE_STARTED")
        assert validate_event_type("PHASE_STARTED") is True
        assert get_event_category("PHASE_STARTED") == "PHASE"

        # SUBAGENT_STOP events
        assert hasattr(EventType, "SUBAGENT_STOP_VALIDATION")
        assert validate_event_type("SUBAGENT_STOP_VALIDATION") is True
        assert get_event_category("SUBAGENT_STOP_VALIDATION") == "SUBAGENT_STOP"

        # COMMIT events
        assert hasattr(EventType, "COMMIT_SUCCESS")
        assert validate_event_type("COMMIT_SUCCESS") is True
        assert get_event_category("COMMIT_SUCCESS") == "COMMIT"

        # VALIDATION events
        assert hasattr(EventType, "VALIDATION_REJECTED")
        assert validate_event_type("VALIDATION_REJECTED") is True
        assert get_event_category("VALIDATION_REJECTED") == "VALIDATION"
