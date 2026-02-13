"""
Unit tests for LoggingPort and its adapters.

Tests validate that LoggingPort interface is correctly defined and that
StructuredLogger and SilentLogger adapters implement the interface correctly.
"""

import json
from io import StringIO


def test_logging_port_interface_defines_required_methods():
    """
    Test that LoggingPort interface defines all required abstract methods.

    Given: LoggingPort interface
    When: Interface is inspected
    Then: All required methods are defined as abstract
    """
    # Verify it's an abstract base class
    from abc import ABC

    from des.ports.driven_ports.logging_port import LoggingPort

    assert issubclass(LoggingPort, ABC)

    # Verify required methods exist
    assert hasattr(LoggingPort, "log_validation_result")
    assert hasattr(LoggingPort, "log_hook_execution")
    assert hasattr(LoggingPort, "log_error")


def test_structured_logger_produces_valid_json_output():
    """
    Test that StructuredLogger produces valid JSON output.

    Given: StructuredLogger instance
    When: log_validation_result is called
    Then: Valid JSON is written to output stream
    """
    from des.adapters.driven.logging.structured_logger import StructuredLogger

    # Capture output
    output = StringIO()
    logger = StructuredLogger(output_stream=output)

    # Create mock validation result
    class MockValidationResult:
        def __init__(self):
            self.is_valid = True
            self.errors = []

    result = MockValidationResult()
    context = {"step_file": "test.json", "turn": 5}

    # Log validation result
    logger.log_validation_result(result, context)

    # Verify JSON output
    output_value = output.getvalue()
    assert output_value.strip()  # Not empty

    # Parse as JSON to verify it's valid
    log_entry = json.loads(output_value.strip())
    assert log_entry["event"] == "validation_result"
    assert log_entry["is_valid"] is True
    assert log_entry["context"]["step_file"] == "test.json"


def test_structured_logger_logs_hook_execution():
    """
    Test that StructuredLogger logs hook execution events.

    Given: StructuredLogger instance
    When: log_hook_execution is called
    Then: Valid JSON log entry is created
    """
    from des.adapters.driven.logging.structured_logger import StructuredLogger

    output = StringIO()
    logger = StructuredLogger(output_stream=output)

    class MockHookResult:
        def __init__(self):
            self.success = True
            self.message = "Hook executed"

    result = MockHookResult()
    step_file = "test_step.json"

    logger.log_hook_execution(result, step_file)

    output_value = output.getvalue()
    log_entry = json.loads(output_value.strip())
    assert log_entry["event"] == "hook_execution"
    assert log_entry["success"] is True
    assert log_entry["step_file"] == "test_step.json"


def test_structured_logger_logs_errors():
    """
    Test that StructuredLogger logs error events.

    Given: StructuredLogger instance
    When: log_error is called
    Then: Error is logged as JSON
    """
    from des.adapters.driven.logging.structured_logger import StructuredLogger

    output = StringIO()
    logger = StructuredLogger(output_stream=output)

    error = ValueError("Test error")
    context = {"operation": "test_operation"}

    logger.log_error(error, context)

    output_value = output.getvalue()
    log_entry = json.loads(output_value.strip())
    assert log_entry["event"] == "error"
    assert "ValueError" in log_entry["error_type"]
    assert "Test error" in log_entry["error_message"]


def test_silent_logger_is_no_op():
    """
    Test that SilentLogger performs no operations (no-op implementation).

    Given: SilentLogger instance
    When: Any logging method is called
    Then: No output is produced and no errors occur
    """
    from des.adapters.driven.logging.silent_logger import SilentLogger

    logger = SilentLogger()

    # Create mock objects
    class MockResult:
        pass

    result = MockResult()
    context = {"test": "context"}

    # Call all methods - should not raise any errors
    logger.log_validation_result(result, context)
    logger.log_hook_execution(result, "test.json")
    logger.log_error(ValueError("test"), context)

    # If we get here, all methods executed without error (no-op)
    assert True


def test_silent_logger_implements_logging_port():
    """
    Test that SilentLogger implements LoggingPort interface.

    Given: SilentLogger class
    When: Class is inspected
    Then: It is an instance of LoggingPort
    """
    from des.adapters.driven.logging.silent_logger import SilentLogger
    from des.ports.driven_ports.logging_port import LoggingPort

    logger = SilentLogger()
    assert isinstance(logger, LoggingPort)


def test_structured_logger_implements_logging_port():
    """
    Test that StructuredLogger implements LoggingPort interface.

    Given: StructuredLogger class
    When: Class is inspected
    Then: It is an instance of LoggingPort
    """
    from des.adapters.driven.logging.structured_logger import StructuredLogger
    from des.ports.driven_ports.logging_port import LoggingPort

    logger = StructuredLogger()
    assert isinstance(logger, LoggingPort)
