"""
Helper functions for DES Installation Bug Acceptance Tests.

These utilities are shared across step definition modules.
Separated to avoid circular imports with conftest.py.
"""

import json
from pathlib import Path


def count_des_hooks(settings_file: Path, hook_type: str) -> int:
    """
    Count DES hooks in settings.json.

    Supports both flat format (old) and nested format (current):
    - Flat: {"command": "...claude_code_hook_adapter..."}
    - Nested: {"hooks": [{"type": "command", "command": "...claude_code_hook_adapter..."}]}

    Args:
        settings_file: Path to settings.json
        hook_type: "PreToolUse" or "SubagentStop"

    Returns:
        Number of DES hooks found
    """
    if not settings_file.exists():
        return 0

    with open(settings_file) as f:
        config = json.load(f)

    hooks = config.get("hooks", {}).get(hook_type, [])
    count = 0
    for h in hooks:
        # Check flat format (old)
        if is_des_hook(h.get("command", "")):
            count += 1
            continue
        # Check nested format (current)
        for inner in h.get("hooks", []):
            if is_des_hook(inner.get("command", "")):
                count += 1
                break
    return count


def is_des_hook(command: str) -> bool:
    """
    Check if a command string is a DES hook command.

    Detects both old and new formats:
    - Old: python3 src/des/.../claude_code_hook_adapter.py
    - New: python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter
    """
    return "claude_code_hook_adapter" in command


def is_des_hook_entry(hook_entry: dict) -> bool:
    """
    Check if a hook entry dict is a DES hook.

    Supports both flat and nested formats:
    - Flat: {"command": "...claude_code_hook_adapter..."}
    - Nested: {"hooks": [{"type": "command", "command": "...claude_code_hook_adapter..."}]}
    """
    if is_des_hook(hook_entry.get("command", "")):
        return True
    for inner in hook_entry.get("hooks", []):
        if is_des_hook(inner.get("command", "")):
            return True
    return False


def scan_for_bad_imports(des_path: Path) -> list[str]:
    """
    Scan installed DES directory for bad import patterns.

    Returns list of files containing "from src.des" or "import src.des".
    """
    bad_files = []
    if not des_path.exists():
        return bad_files

    for py_file in des_path.rglob("*.py"):
        try:
            content = py_file.read_text()
            if "from src.des" in content or "import src.des" in content:
                bad_files.append(str(py_file))
        except Exception:
            pass

    return bad_files
