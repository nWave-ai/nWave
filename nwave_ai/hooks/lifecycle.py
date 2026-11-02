"""SessionStart/SessionEnd registration in the global activity registry, and the shared subagent
identity resolution that identity-aware hooks use.

Every host session that reaches the installed lifecycle hooks is recorded under the selected
agents home, whether or not its project is activated and whether or not any update permission is
granted: an update replaces the installation shared by every repository, so an unrecorded session
would be invisible to it. Registration waits for the exclusive update lock, but native SessionStart
hooks cannot prove that their host withheld work. A timeout still records the session and returns
an explicit failed admission plus a warning. Both functions are total.

Moved verbatim from the removed DES runtime (S5-OQ6 closure of the hook handlers).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from nwave_ai.platform.session_registry import (
    MANAGED_SESSION_ENV,
    SessionActivityRegistry,
    session_key,
)
from nwave_ai.platform.update_timing import UPDATE_TIMING


REGISTRATION_WAIT_SECONDS = UPDATE_TIMING.admission_seconds
DEREGISTRATION_WAIT_SECONDS = UPDATE_TIMING.session_end_seconds

_NWAVE_AGENT_PREFIX = "nw-"


@dataclass(frozen=True)
class Registration:
    """Outcome of one SessionStart registration attempt."""

    key: str | None
    waited_for_update: bool = False
    notice: str = ""
    admission_state: Literal["admitted", "busy", "unknown", "update-incomplete"] = (
        "unknown"
    )

    @property
    def admitted(self) -> bool:
        """Positive coordination result, not evidence of native host blocking."""
        return self.admission_state == "admitted"


def _event(stdin_text: str) -> dict:
    try:
        event = json.loads(stdin_text)
    except (TypeError, json.JSONDecodeError):
        return {}
    return event if isinstance(event, dict) else {}


def register_session_start(stdin_text: str, host: str) -> Registration:
    """Record this host session; never raises."""
    try:
        registry = SessionActivityRegistry.selected()
        if registry is None:
            return Registration(
                key=None,
                notice=(
                    "nWave session admission is unknown: the activity registry could "
                    "not be resolved. Installation safety is not established; repair "
                    "the selected installation before starting wave work."
                ),
            )
        managed_key = os.environ.get(MANAGED_SESSION_ENV)
        if managed_key and any(
            record.key == managed_key
            and record.host == f"managed:{host}"
            and not record.problem
            for record in registry.sessions()
        ):
            # The wrapper, not a native inner session-end event, owns this lifetime.
            return Registration(key=managed_key, admission_state="admitted")
        event = _event(stdin_text)
        raw_id = event.get("session_id")
        session_id = raw_id if isinstance(raw_id, str) and raw_id else None
        cwd = event.get("cwd") if isinstance(event.get("cwd"), str) else ""
        source = event.get("source") if isinstance(event.get("source"), str) else ""
        started = time.monotonic()
        with registry.exclusive(REGISTRATION_WAIT_SECONDS) as acquired:
            key = registry.register(
                host=host, session_id=session_id, cwd=cwd, source=source
            )
            marker = registry.update_in_progress() if acquired else None
        waited = time.monotonic() - started > 2.0
        if not acquired:
            return Registration(
                key=key,
                waited_for_update=True,
                admission_state="busy",
                notice=(
                    "nWave session admission timed out: another session still holds "
                    "the installation update lock. The host may not block work on "
                    "this warning. Close this session; restart after the update finishes."
                ),
            )
        if marker is not None:
            return Registration(
                key=key,
                waited_for_update=waited,
                admission_state="update-incomplete",
                notice=(
                    "nWave session admission refused: an unfinished update is recorded; "
                    "package or host state is unknown. The host may not block work on "
                    "this warning. Close this session and inspect the update recovery "
                    "state before restarting."
                ),
            )
        return Registration(
            key=key, waited_for_update=waited, admission_state="admitted"
        )
    except Exception:
        return Registration(
            key=None,
            notice=(
                "nWave session admission is unknown: the activity registry could not "
                "record or verify this session. Installation safety is not established; "
                "repair the registry before starting wave work."
            ),
        )


def handle_session_end(stdin_text: str, host: str) -> int:
    """Remove this host session's record; always exits 0."""
    try:
        registry = SessionActivityRegistry.selected()
        raw_id = _event(stdin_text).get("session_id")
        if registry is None or not isinstance(raw_id, str) or not raw_id:
            return 0
        key = session_key(host, raw_id)
        with registry.exclusive(DEREGISTRATION_WAIT_SECONDS):
            # A session that ended cannot be running a wave, so removal is
            # safe even when an update still holds the lock.
            registry.deregister(key)
    except Exception:
        pass
    return 0


# ---------------------------------------------------------------------------
# Shared subagent identity resolution for identity-aware hooks
# ---------------------------------------------------------------------------
# An ordinary PreToolUse envelope carries neither agent_id nor agent_type reliably. Identity is
# resolved from the live envelope first, then from the platform's durable subagents/agent-<id>
# .meta.json sidecar written at spawn time next to each dispatched subagent's own transcript.


def _agent_type_from_transcript_meta_sidecar(transcript_path: str) -> str | None:
    """The `agentType` recorded in a subagent transcript's `.meta.json` sidecar.

    `None` when the path is not a `subagents/agent-<id>.jsonl` transcript, when
    no readable sidecar sits next to it, or when its JSON carries no string
    `agentType`.
    """
    path = Path(transcript_path)
    if path.parent.name != "subagents" or not path.name.startswith("agent-"):
        return None
    meta_path = path.parent / f"{path.stem}.meta.json"
    try:
        meta_text = meta_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        meta = json.loads(meta_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(meta, dict):
        return None
    sidecar_agent_type = meta.get("agentType")
    return sidecar_agent_type if isinstance(sidecar_agent_type, str) else None


def resolve_subagent_own_transcript_path(hook_input: dict[str, object]) -> str | None:
    """The dispatched subagent's OWN transcript file.

    A dispatched subagent's `transcript_path` usually names the ROOT session log
    (`<session-id>.jsonl`), a sibling of the `<session-id>/subagents/` directory
    that holds each dispatched subagent's own transcript -- not the subagent's
    own file. Returns `transcript_path` unchanged when it already has the
    subagent shape, otherwise derives the real file from that structural
    convention plus `agent_id`, using it only when it exists on disk. Falls
    through to `transcript_path` unchanged when neither succeeds.
    """
    transcript_path = hook_input.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    path = Path(transcript_path)
    if path.parent.name == "subagents" and path.name.startswith("agent-"):
        return transcript_path
    agent_id = hook_input.get("agent_id")
    if isinstance(agent_id, str) and agent_id and path.suffix == ".jsonl":
        derived = path.parent / path.stem / "subagents" / f"agent-{agent_id}.jsonl"
        if derived.is_file():
            return str(derived)
    return transcript_path


def resolve_subagent_agent_type(hook_input: dict[str, object]) -> str | None:
    """The dispatched nw-* subagent's own declared role name.

    Resolved from the live envelope's `agent_type` field first (cheap, no I/O),
    falling back to the transcript meta-sidecar (one extra read) only when that
    field is absent or names a non-`nw-` role. `None` for root/user (no
    resolvable identity from either source) and for a non-nWave agent.
    """
    agent_type = hook_input.get("agent_type")
    if isinstance(agent_type, str) and agent_type.startswith(_NWAVE_AGENT_PREFIX):
        return agent_type
    own_transcript_path = resolve_subagent_own_transcript_path(hook_input)
    if own_transcript_path is None:
        return None
    sidecar_agent_type = _agent_type_from_transcript_meta_sidecar(own_transcript_path)
    if isinstance(sidecar_agent_type, str) and sidecar_agent_type.startswith(
        _NWAVE_AGENT_PREFIX
    ):
        return sidecar_agent_type
    return None
