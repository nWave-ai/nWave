"""JsonlSkillTracker - driven adapter for skill loading observability.

Implements the SkillTrackingPort by appending events to a JSONL file.
Fail-silent: never raises exceptions that could block agent execution.

Output: .nwave/skill-loading-log.jsonl (one JSON object per line)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from des.domain.nwave_dir_gitignore import ensure_nwave_gitignore
from des.ports.driven_ports.skill_tracking_port import SkillTrackingPort


if TYPE_CHECKING:
    from des.domain.skill_load_event import SkillLoadEvent


class JsonlSkillTracker(SkillTrackingPort):
    """Appends skill load events to a JSONL file.

    Each event is serialized as one JSON line, appended to the log file.
    Creates the .nwave/ directory if it does not exist.
    Fail-silent: all I/O errors are swallowed.
    """

    DEFAULT_LOG_FILE = ".nwave/skill-loading-log.jsonl"

    def __init__(self, log_path: str | Path | None = None) -> None:
        """Initialize with optional log file path.

        Args:
            log_path: Path to the JSONL log file.
                      Defaults to .nwave/skill-loading-log.jsonl in cwd.
        """
        if log_path is None:
            self._log_path = Path.cwd() / self.DEFAULT_LOG_FILE
        else:
            self._log_path = Path(log_path)

    def log_skill_load(self, event: SkillLoadEvent) -> None:
        """Append a skill load event to the JSONL log file.

        Fail-silent: any I/O error is swallowed to avoid blocking execution.

        Args:
            event: The skill load event to log
        """
        try:
            self._ensure_directory()
            self._append_event(event)
        except Exception:
            pass  # Fail-silent: tracking must never block agent execution

    def _ensure_directory(self) -> None:
        """Create parent directory if it does not exist."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_nwave_gitignore(self._log_path.parent)

    def _append_event(self, event: SkillLoadEvent) -> None:
        """Serialize and append event as a JSON line."""
        json_line = json.dumps(event.to_dict(), separators=(",", ":"), sort_keys=True)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")
