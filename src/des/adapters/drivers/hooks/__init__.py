"""Hook driver adapters.

Legacy SubagentStopHook removed. Production validation uses
claude_code_hook_adapter -> SubagentStopService.

MockedSubagentStopHook retained for orchestrator tests that need a HookPort stub.
"""

from des.adapters.drivers.hooks.mocked_hook import MockedSubagentStopHook


__all__ = ["MockedSubagentStopHook"]
