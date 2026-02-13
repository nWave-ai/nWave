"""Task invocation driven adapters."""

from des.adapters.driven.task_invocation.claude_code_task_adapter import (
    ClaudeCodeTaskAdapter,
)
from des.adapters.driven.task_invocation.mocked_task_adapter import (
    MockedTaskAdapter,
)


__all__ = ["ClaudeCodeTaskAdapter", "MockedTaskAdapter"]
