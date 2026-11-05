"""A sub-agent must not write into the root checkout while lanes are live.

The edit tool resolves a relative path against the session's working directory, which for a
sub-agent is the root checkout, not the lane it was sent to work in. A relative path written by
a lane agent therefore lands on trunk, where only the root orchestrator writes. This module
decides that one case from declared facts: the caller is a sub-agent, the project declares lanes
in ``.nwave/config.json`` and has at least one lane under ``lanes/``, and the resolved target lies in the root
checkout outside ``lanes/``. A root session, a project without lanes, an absolute lane path
and a path outside the checkout are all allowed.

REMOVE when the host resolves a sub-agent's relative paths against its own working directory.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


LANES_DIR = "lanes"


def live_lanes(root: Path) -> tuple[str, ...]:
    """The lanes open under ``root/lanes``, by name (the shell side of the decision).

    Only a project that declares lanes in ``.nwave/config.json`` has any: a folder that merely
    happens to be named ``lanes`` is not a declaration.
    """
    try:
        config = json.loads(
            (root / ".nwave" / "config.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return ()
    lanes = root / LANES_DIR
    if not (isinstance(config, dict) and isinstance(config.get("lanes"), dict)):
        return ()
    if not lanes.is_dir():
        return ()
    return tuple(sorted(entry.name for entry in lanes.iterdir() if entry.is_dir()))


def _inside(path: str, directory: str) -> bool:
    return path == directory or path.startswith(directory + os.sep)


def root_checkout_write_refusal(
    file_path: str, cwd: str, agent_type: str | None, lanes: tuple[str, ...]
) -> str | None:
    """WHAT/WHY/HOW text when a sub-agent writes the root checkout while lanes are live."""
    if not (agent_type and file_path and cwd and lanes):
        return None
    root = os.path.normpath(cwd)
    target = os.path.normpath(os.path.join(root, file_path))
    if not _inside(target, root) or _inside(target, os.path.join(root, LANES_DIR)):
        return None
    relative = os.path.relpath(target, root)
    own = os.path.join(root, LANES_DIR, "<your-lane>", relative)
    return (
        f"WHAT: {agent_type} tried to write {target} in the root checkout {root} "
        f"while lanes are live ({', '.join(lanes)}).\n"
        "WHY: only the root orchestrator writes the root checkout. The edit tool resolves a "
        "relative path against the root checkout, not against your lane, so a relative path "
        "lands on trunk.\n"
        f"HOW: write the same file by its absolute path under YOUR OWN lane: {own}. "
        "Never write under another lane. If you were sent to change the root checkout itself, "
        "report that to the root instead."
    )
