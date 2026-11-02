"""Shell fast-path guard of the kept Write and Edit hook registrations.

The guard buffers the hook input and starts Python only when the write can need a decision:
an execution-log target, or a project that carries ``.nwave/config.json``. Every other write
exits 0 without starting Python. The shell never parses JSON or interprets activation state:
that remains the sole responsibility of the Python handler.
"""

from __future__ import annotations


__all__ = ["build_guard_command"]


def build_guard_command(python_cmd: str) -> str:
    """Build the shell fast-path guard command template for Write/Edit hooks.

    The guard:
    1. Buffers stdin (hook input JSON).
    2. If the target is execution-log.json, always invokes Python (unconditional).
    3. Invokes Python when the canonical `.nwave/config.json` exists in the project -- a
       content-blind shell-level pre-filter (file EXISTENCE only, never an activation value
       or any other JSON). Activation resolution and target pertinence stay in Python.
    4. Otherwise, exits 0 (fast path, unchanged for irrelevant or out-of-tree writes).

    Args:
        python_cmd: The full Python command string (PYTHONPATH=... python3 -m ...)
            WITHOUT the action suffix. The action will be appended by the caller.

    Returns:
        Shell command template string. The caller must format it with the action.
    """
    return (  # noqa: UP032 -- .format() required for shell template with literal braces
        "INPUT=$(cat); "
        "printf '%s' \"$INPUT\" | grep -q 'execution-log\\.json' && "
        "{{ printf '%s' \"$INPUT\" | {python_cmd}; exit $?; }}; "
        "test -f .nwave/config.json && "
        "{{ printf '%s' \"$INPUT\" | {python_cmd}; exit $?; }}; "
        "exit 0"
    ).format(python_cmd=python_cmd)
