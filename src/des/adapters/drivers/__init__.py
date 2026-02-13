"""
DES Driver Adapters - Primary/Inbound adapter implementations.

Exports all driver adapter implementations that serve as entry points to DES.

Legacy SubagentStopHook removed. Production validation uses
claude_code_hook_adapter -> SubagentStopService.

Backward compatibility aliases kept for RealSubagentStopHook/RealHook
pointing to None (removed).
"""

__all__: list[str] = []
