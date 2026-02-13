"""DES marker parser domain logic.

Pure business rule for detecting and parsing DES HTML comment markers
in Task prompts. No I/O dependencies.

Replaces inline regex in claude_code_hook_adapter.handle_pre_tool_use()
(lines 123-134).

Marker formats:
  <!-- DES-VALIDATION : required -->
  <!-- DES-MODE : orchestrator -->
  <!-- DES-PROJECT-ID : my-project -->
  <!-- DES-STEP-ID : 01-01 -->
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DesMarkers:
    """Parsed DES markers from a Task prompt.

    Attributes:
        is_des_task: True if prompt contains DES-VALIDATION: required marker
        is_orchestrator_mode: True if prompt contains DES-MODE: orchestrator marker
        project_id: Value of DES-PROJECT-ID marker, or None
        step_id: Value of DES-STEP-ID marker, or None
    """

    is_des_task: bool
    is_orchestrator_mode: bool
    project_id: str | None = None
    step_id: str | None = None


class DesMarkerParser:
    """Parses DES HTML comment markers from Task prompts.

    This is a stateless parser with no I/O dependencies.
    All patterns are compiled once at class level for efficiency.
    """

    _VALIDATION_PATTERN = re.compile(r"<!--\s*DES-VALIDATION\s*:\s*required\s*-->")
    _MODE_PATTERN = re.compile(r"<!--\s*DES-MODE\s*:\s*orchestrator\s*-->")
    _PROJECT_ID_PATTERN = re.compile(r"<!--\s*DES-PROJECT-ID\s*:\s*(\S+)\s*-->")
    _STEP_ID_PATTERN = re.compile(r"<!--\s*DES-STEP-ID\s*:\s*(\S+)\s*-->")

    def parse(self, prompt: str) -> DesMarkers:
        """Parse DES markers from a Task prompt string.

        Args:
            prompt: Full Task prompt text

        Returns:
            DesMarkers with detected marker values
        """
        is_des_task = bool(self._VALIDATION_PATTERN.search(prompt))
        is_orchestrator_mode = bool(self._MODE_PATTERN.search(prompt))

        project_id_match = self._PROJECT_ID_PATTERN.search(prompt)
        project_id = project_id_match.group(1) if project_id_match else None

        step_id_match = self._STEP_ID_PATTERN.search(prompt)
        step_id = step_id_match.group(1) if step_id_match else None

        return DesMarkers(
            is_des_task=is_des_task,
            is_orchestrator_mode=is_orchestrator_mode,
            project_id=project_id,
            step_id=step_id,
        )
