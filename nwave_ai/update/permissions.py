"""Read explicit update permissions and the separate controlled-launch commitment."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _updates() -> dict:
    from nwave_ai.platform.locations import NWaveLocations
    from nwave_ai.platform.result import Failure

    located = NWaveLocations.resolve(
        home=Path.home(),
        repo_root=Path.cwd(),
        agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
        claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
        codex_config_override=os.environ.get("CODEX_HOME"),
    )
    if isinstance(located, Failure):
        return {}
    try:
        path = located.unwrap().agents_home / ".nwave" / "config.json"
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    updates = document.get("updates") if isinstance(document, dict) else None
    return updates if isinstance(updates, dict) else {}


def update_permissions() -> tuple[bool, bool]:
    updates = _updates()
    return updates.get("check") is True, updates.get("install") is True


def controlled_launch_permission() -> bool:
    return _updates().get("controlled_launch") is True
