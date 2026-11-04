"""Skill-loading observability for the hook handlers: a Read of a skill file in a sub-agent
transcript is logged as one JSONL event for token-cost analysis.

Moved verbatim from the removed DES runtime (S5-OQ6 closure of the hook handlers). All tracking is
fail-open: it never blocks agent execution.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nwave_ai.hooks.run_context import SystemTimeProvider, TimeProvider
from nwave_ai.platform.config import NWaveConfig
from nwave_ai.platform.gitignore import ensure_nwave_gitignore
from nwave_ai.platform.project_root import anchor_to_project_root


@dataclass(frozen=True)
class SkillLoadEvent:
    """Value object representing a skill file being loaded by an agent.

    Attributes:
        timestamp: ISO 8601 UTC timestamp of the load event
        agent_name: Agent that loaded the skill (e.g., "software-crafter")
        skill_name: Name of the skill loaded (e.g., "tdd-methodology")
        file_path: Full path to the skill file
        estimated_tokens: Estimated token count (chars // 4)
        step_id: DES step identifier, if available
    """

    timestamp: str
    agent_name: str
    skill_name: str
    file_path: str
    estimated_tokens: int
    step_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization. Excludes None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class SkillTrackingPort(ABC):
    """Driven port: logs skill load events for observability.

    Events are append-only. Implementations must be fail-silent
    (never raise exceptions that could block agent execution).
    """

    @abstractmethod
    def log_skill_load(self, event: SkillLoadEvent) -> None:
        """Log a skill load event."""
        ...


class JsonlSkillTracker(SkillTrackingPort):
    """Appends skill load events to a JSONL file. Fail-silent: all I/O errors are swallowed.

    Output: <project root>/.nwave/skill-loading-log.jsonl (one JSON object per line).
    """

    DEFAULT_LOG_FILE = ".nwave/skill-loading-log.jsonl"

    def __init__(self, log_path: str | Path | None = None) -> None:
        """Initialize with optional log file path (default: project-root log file)."""
        if log_path is None:
            self._log_path = anchor_to_project_root(Path.cwd()) / self.DEFAULT_LOG_FILE
        else:
            self._log_path = Path(log_path)

    def log_skill_load(self, event: SkillLoadEvent) -> None:
        """Append a skill load event to the JSONL log file. Fail-silent."""
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


def extract_tool_calls(entry: dict) -> list[dict]:
    """Extract every tool_use dict from a transcript entry.

    Stateless parse of the captured-trace JSONL shape. Supports three formats:
    - Direct: {"type": "tool_use", "name": "Read", "input": {...}}
    - Content block: {"type": "content_block", "content_block": {"type": "tool_use", ...}}
    - Real Claude Code transcript:
      {"type": "assistant", "message": {"content": [{"type": "tool_use", ...}, ...]}}

    Returns the tool_use dicts (each with 'name' and 'input' keys); empty when none.
    """
    entry_type = entry.get("type", "")
    if entry_type == "tool_use":
        return [entry]
    if entry_type == "content_block":
        block = entry.get("content_block", {})
        return [block] if block.get("type") == "tool_use" else []
    if entry_type != "assistant":
        return []
    message = entry.get("message", {})
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        return [
            block
            for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"
        ]
    return []


def read_transcript_tool_calls(transcript_path: str) -> list[dict]:
    """Read a JSONL transcript and extract its tool_use entries. Malformed lines are skipped."""
    tool_calls: list[dict] = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            tool_calls.extend(extract_tool_calls(entry))
    return tool_calls


class SkillTrackingService:
    """Tracks skill file loads for observability.

    Entry point: track_from_transcript() is called from the SubagentStop
    hook with a sub-agent's full JSONL transcript.
    """

    SKILL_PATH_MARKER = "/skills/nw/"

    def __init__(
        self,
        tracker: SkillTrackingPort,
        time_provider: TimeProvider,
        strategy: str = "token-tracking",
    ) -> None:
        """Initialize with dependencies (strategy: "token-tracking" or "passive-logging")."""
        self._tracker = tracker
        self._time = time_provider
        self._strategy = strategy

    def _is_skill_read(self, tool_name: str, tool_input: dict) -> bool:
        """Check if this tool call is a Read of a skill file."""
        return tool_name == "Read" and self.SKILL_PATH_MARKER in tool_input.get(
            "file_path", ""
        )

    def _parse_skill_info(self, file_path: str) -> tuple[str, str]:
        """Extract (agent_name, skill_name) from a path .../skills/nw/{agent}/{skill}.md."""
        marker_idx = file_path.index(self.SKILL_PATH_MARKER) + len(
            self.SKILL_PATH_MARKER
        )
        remainder = file_path[marker_idx:]
        parts = remainder.split("/")
        agent_name = parts[0] if len(parts) >= 2 else "unknown"
        skill_name = (
            parts[1].removesuffix(".md")
            if len(parts) >= 2
            else remainder.removesuffix(".md")
        )
        return agent_name, skill_name

    def _estimate_tokens(self, file_path: str) -> int:
        """Estimate token count from file size (chars // 4). 0 if unavailable."""
        if self._strategy != "token-tracking":
            return 0
        try:
            resolved = Path(file_path).expanduser()
            if resolved.exists():
                return len(resolved.read_text(encoding="utf-8")) // 4
        except (OSError, UnicodeDecodeError):
            # WHAT: file vanished/unreadable or has undecodable bytes between
            # the exists() check and read_text().
            # WHY: token estimation is best-effort observability, not
            # correctness-critical (see module docstring: "Fail-open").
            # HOW: safe to continue -- caller falls back to the 0 default.
            pass
        return 0

    def track_from_transcript(self, transcript_path: str) -> list[SkillLoadEvent]:
        """Extract and log skill loads from a sub-agent JSONL transcript. Fail-open."""
        try:
            tool_calls = self._read_transcript_tool_calls(transcript_path)
            skill_reads = self._filter_skill_reads(tool_calls)
            events = self._build_events(skill_reads)
            self._log_events(events)
            return events
        except Exception:
            return []  # Fail-open: tracking must never block

    def _read_transcript_tool_calls(self, transcript_path: str) -> list[dict]:
        """Read JSONL transcript and extract tool_use entries."""
        return read_transcript_tool_calls(transcript_path)

    def _filter_skill_reads(self, tool_calls: list[dict]) -> list[dict]:
        """Filter to only Read calls targeting skill files."""
        return [
            tc
            for tc in tool_calls
            if self._is_skill_read(tc.get("name", ""), tc.get("input", {}))
        ]

    def _build_events(self, skill_reads: list[dict]) -> list[SkillLoadEvent]:
        """Build SkillLoadEvent objects from filtered skill Read calls."""
        events: list[SkillLoadEvent] = []
        for tc in skill_reads:
            file_path = tc.get("input", {}).get("file_path", "")
            agent_name, skill_name = self._parse_skill_info(file_path)
            estimated_tokens = self._estimate_tokens(file_path)
            event = SkillLoadEvent(
                timestamp=self._time.now_utc().isoformat(),
                agent_name=agent_name,
                skill_name=skill_name,
                file_path=file_path,
                estimated_tokens=estimated_tokens,
            )
            events.append(event)
        return events

    def _log_events(self, events: list[SkillLoadEvent]) -> None:
        """Log all events via the tracker port."""
        for event in events:
            self._tracker.log_skill_load(event)


def maybe_track_skill_loads(transcript_path: str) -> None:
    """Track skill file reads from a sub-agent JSONL transcript. Fail-open.

    Scans the transcript for Read tool calls targeting /skills/nw/ paths
    and logs each as a SkillLoadEvent.
    """
    try:
        config = NWaveConfig()
        if not config.skill_tracking_enabled:
            return
        tracker = JsonlSkillTracker()
        service = SkillTrackingService(
            tracker=tracker,
            time_provider=SystemTimeProvider(),
            strategy=config.skill_tracking_strategy,
        )
        service.track_from_transcript(transcript_path)
    except Exception:
        pass  # Fail-open: tracking must never block sub-agent completion
