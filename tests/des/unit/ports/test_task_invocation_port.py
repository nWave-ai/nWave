"""
Unit tests for TaskInvocationPort and its adapters.

Tests validate that TaskInvocationPort interface is correctly defined and that
ClaudeCodeTaskAdapter and MockedTaskAdapter implement the interface correctly.
"""


def test_task_invocation_port_interface_defines_required_methods():
    """
    Test that TaskInvocationPort interface defines all required abstract methods.

    Given: TaskInvocationPort interface
    When: Interface is inspected
    Then: invoke_task method is defined as abstract
    """
    # Verify it's an abstract base class
    from abc import ABC

    from des.ports.driven_ports.task_invocation_port import TaskInvocationPort

    assert issubclass(TaskInvocationPort, ABC)

    # Verify required method exists
    assert hasattr(TaskInvocationPort, "invoke_task")


def test_mocked_task_adapter_returns_predefined_results():
    """
    Test that MockedTaskAdapter returns predefined TaskResult.

    Given: MockedTaskAdapter with predefined results
    When: invoke_task is called
    Then: Predefined result is returned
    """
    from des.adapters.driven.task_invocation.mocked_task_adapter import (
        MockedTaskAdapter,
    )

    # Create adapter with predefined result
    predefined_result = {"success": True, "output": "Test output", "error": None}
    adapter = MockedTaskAdapter(predefined_result=predefined_result)

    # Invoke task
    result = adapter.invoke_task("test prompt", "test-agent")

    # Verify predefined result is returned
    assert result["success"] is True
    assert result["output"] == "Test output"
    assert result["error"] is None


def test_mocked_task_adapter_supports_multiple_results():
    """
    Test that MockedTaskAdapter can return different results for different calls.

    Given: MockedTaskAdapter with multiple predefined results
    When: invoke_task is called multiple times
    Then: Results are returned in sequence
    """
    from des.adapters.driven.task_invocation.mocked_task_adapter import (
        MockedTaskAdapter,
    )

    results_queue = [
        {"success": True, "output": "First call"},
        {"success": True, "output": "Second call"},
        {"success": False, "error": "Third call failed"},
    ]

    adapter = MockedTaskAdapter(results_queue=results_queue)

    # First call
    result1 = adapter.invoke_task("prompt1", "agent1")
    assert result1["output"] == "First call"

    # Second call
    result2 = adapter.invoke_task("prompt2", "agent2")
    assert result2["output"] == "Second call"

    # Third call
    result3 = adapter.invoke_task("prompt3", "agent3")
    assert result3["success"] is False
    assert result3["error"] == "Third call failed"


def test_mocked_task_adapter_implements_task_invocation_port():
    """
    Test that MockedTaskAdapter implements TaskInvocationPort interface.

    Given: MockedTaskAdapter class
    When: Class is inspected
    Then: It is an instance of TaskInvocationPort
    """
    from des.adapters.driven.task_invocation.mocked_task_adapter import (
        MockedTaskAdapter,
    )
    from des.ports.driven_ports.task_invocation_port import TaskInvocationPort

    adapter = MockedTaskAdapter()
    assert isinstance(adapter, TaskInvocationPort)


def test_claude_code_task_adapter_implements_task_invocation_port():
    """
    Test that ClaudeCodeTaskAdapter implements TaskInvocationPort interface.

    Given: ClaudeCodeTaskAdapter class
    When: Class is inspected
    Then: It is an instance of TaskInvocationPort
    """
    from des.adapters.driven.task_invocation.claude_code_task_adapter import (
        ClaudeCodeTaskAdapter,
    )
    from des.ports.driven_ports.task_invocation_port import TaskInvocationPort

    adapter = ClaudeCodeTaskAdapter()
    assert isinstance(adapter, TaskInvocationPort)
