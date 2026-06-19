"""Hook adapter CLI entry point — routes commands to handler modules.

This is the thin dispatcher that replaces the monolithic main() function.
Each handler is in its own module for single-responsibility.

Entry point: python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter <command>
"""

import io
import json
import sys

from des.adapters.drivers.hooks.activation_gate import apply_gate
from des.adapters.drivers.hooks.deliver_progress_handler import handle_deliver_progress
from des.adapters.drivers.hooks.post_tool_use_handler import handle_post_tool_use
from des.adapters.drivers.hooks.pre_tool_use_handler import handle_pre_tool_use
from des.adapters.drivers.hooks.pre_write_handler import handle_pre_write
from des.adapters.drivers.hooks.session_start_handler import handle_session_start
from des.adapters.drivers.hooks.subagent_start_handler import handle_subagent_start
from des.adapters.drivers.hooks.subagent_stop_handler import handle_subagent_stop


def main() -> None:
    """Hook adapter entry point - routes command to appropriate handler."""
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "Missing command argument (pre-tool-use or subagent-stop)",
                }
            )
        )
        sys.exit(1)

    command = sys.argv[1]

    # Activation gate (ADR-AG-001): buffer stdin at the top, before any handler
    # reads it, so the gate can resolve the project and re-inject the bytes
    # byte-identically. Inactive non-SessionStart commands exit 0 (allow, never
    # block) inside apply_gate. SessionStart is exempt (always dispatches). The
    # read is defensive (fail-open): an unreadable stdin yields an empty buffer.
    try:
        buffered_stdin = sys.stdin.read()
    except (OSError, ValueError):
        buffered_stdin = ""
    reinjected = apply_gate(command, buffered_stdin)
    sys.stdin = io.StringIO(reinjected if reinjected is not None else buffered_stdin)

    if command in ("pre-tool-use", "pre-task"):
        # "pre-task" accepted for backward compatibility
        exit_code = handle_pre_tool_use()
    elif command == "subagent-stop":
        exit_code = handle_subagent_stop()
    elif command == "deliver-progress":
        exit_code = handle_deliver_progress()
    elif command == "post-tool-use":
        exit_code = handle_post_tool_use()
    elif command in ("pre-write", "pre-edit"):
        exit_code = handle_pre_write()
    elif command == "session-start":
        exit_code = handle_session_start()
    elif command == "subagent-start":
        exit_code = handle_subagent_start()
    else:
        print(json.dumps({"status": "error", "reason": f"Unknown command: {command}"}))
        exit_code = 1

    sys.exit(exit_code)
