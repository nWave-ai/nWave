"""Entry point of the kept hook registrations: ``python -m nwave_ai.hooks EVENT --host H``.

Each kept registration (nwave_ai.hooks.registration) names only its event and its host. This
entry point chooses the handler action from the event and, for PreToolUse, from the tool named
in the hook payload, then runs the handler IN-PROCESS (F229): dispatch, stdin buffering, Codex
envelope normalisation and exit codes moved verbatim from the removed DES hook router, with no
import of it. Handler homes (F238): this module carries the activation gate, the PreToolUse /
PreWrite / SubagentStop handler bodies and the freshness call; the git-stash Bash guard lives in
nwave_ai.hooks.stash, the commit-attribution mutation in nwave_ai.hooks.attribution, the
subagent host-scan limit in nwave_ai.hooks.host_scan; session lifecycle, notices, protocol
logging, skill tracking, run context and audit stay in their sibling modules.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from nwave_ai.hooks import lane_guard
from nwave_ai.hooks.attribution import emit_commit_attribution_mutation
from nwave_ai.hooks.audit import AuditEvent
from nwave_ai.hooks.freshness import assert_fresh_or_explain
from nwave_ai.hooks.host_scan import (
    _evaluate_nwave_subagent_host_scan,
    _is_nwave_subagent,
)
from nwave_ai.hooks.hosts import (
    EXIT_CODE_TO_DECISION,
    STDERR_CAPTURE_MAX_CHARS,
    HookCompletion,
    TaskAccounting,
    get_audit_writer,
    log_hook_completed,
    log_hook_error,
    log_hook_invoked,
    read_and_parse_stdin,
)
from nwave_ai.hooks.lifecycle import handle_session_end, register_session_start
from nwave_ai.hooks.notice import emit_admission_warning, handle_session_start
from nwave_ai.hooks.run_context import DES_TASK_ACTIVE_FILE, SystemTimeProvider
from nwave_ai.hooks.run_context import remove_signal as _remove_task_signal
from nwave_ai.hooks.skill_tracking import maybe_track_skill_loads
from nwave_ai.hooks.stash import evaluate_bash_safety_guards
from nwave_ai.platform.activation import resolve_activation
from nwave_ai.platform.config import NWaveConfig
from nwave_ai.platform.locations import NWaveLocations, resolve_nwave_root
from nwave_ai.platform.result import Failure


EVENTS = ("PreToolUse", "SubagentStop", "SessionStart", "SessionEnd")
HOSTS = ("claude", "codex", "cursor", "copilot", "omp", "opencode")
_EVENT_ACTIONS = {
    "SubagentStop": "subagent-stop",
    "SessionStart": "session-start",
    "SessionEnd": "session-end",
}
_PRE_TOOL_ACTIONS = {"Agent": "pre-task", "Write": "pre-write", "Edit": "pre-edit"}


def action_for(event: str, payload: str) -> str:
    """Handler action of one kept registration: the event, refined by the PreToolUse tool."""
    if event != "PreToolUse":
        return _EVENT_ACTIONS[event]
    return _PRE_TOOL_ACTIONS.get(_tool_name(payload), "pre-tool-use")


def _tool_name(payload: str) -> str:
    try:
        hook_input = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    tool = hook_input.get("tool_name") if isinstance(hook_input, dict) else None
    return tool if isinstance(tool, str) else ""


# ---------------------------------------------------------------------------
# Codex envelope normalisation (verbatim from the removed hook router)
# ---------------------------------------------------------------------------

_PRE_TOOL_USE_COMMANDS = ("pre-tool-use", "pre-task")


def normalize_exec_command_envelope(command: str, stdin_text: str) -> str:
    """Project Codex's exec_command shape onto the Bash safety authority."""
    if command not in _PRE_TOOL_USE_COMMANDS:
        return stdin_text
    try:
        hook_input = json.loads(stdin_text)
    except (json.JSONDecodeError, TypeError):
        return stdin_text
    if (
        not isinstance(hook_input, dict)
        or hook_input.get("tool_name") != "exec_command"
    ):
        return stdin_text
    tool_input = hook_input.get("tool_input")
    if not isinstance(tool_input, dict) or not isinstance(tool_input.get("cmd"), str):
        return stdin_text
    normalized = dict(hook_input)
    normalized["tool_name"] = "Bash"
    normalized["tool_input"] = {**tool_input, "command": tool_input["cmd"]}
    return json.dumps(normalized)


def apply_bash_safety_guards(command: str, stdin_text: str) -> None:
    """Git-stash safety decision (ADR-AG-001 repair).

    Runs BEFORE the activation gate: an inactive project must not be
    able to exit 0 past a live `git stash` mutation. Evaluated exactly once
    per PreToolUse/pre-task dispatch, regardless of activation state, via the
    single decision authority in ``nwave_ai.hooks.stash``
    (:func:`evaluate_bash_safety_guards`).

    Fail-open on a non-PreToolUse command, non-JSON/non-dict envelope, or a
    non-Bash tool_name -- identical parse tolerance to the gate's own
    ``_parse_cwd``, since the gate right after this call already owns "no
    readable envelope -> inactive -> allow". Blocks by printing the guard's
    structured payload and calling ``sys.exit(2)``, matching the existing
    block exit-code convention.
    """
    if command not in _PRE_TOOL_USE_COMMANDS:
        return
    try:
        hook_input = json.loads(stdin_text)
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(hook_input, dict) or hook_input.get("tool_name") != "Bash":
        return
    tool_input = hook_input.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return
    block = evaluate_bash_safety_guards(hook_input, tool_input)
    if block is not None:
        print(json.dumps(block))
        sys.exit(2)


# ---------------------------------------------------------------------------
# Activation gate (ADR-AG-001; verbatim from the removed activation_gate)
# ---------------------------------------------------------------------------


class GateOutcome(Enum):
    """What the gate did with a hook invocation (production-side)."""

    ALLOWED_EXIT_0 = "allowed-exit-0"  # inactive -> sys.exit(0), handler skipped
    DISPATCHED = "dispatched"  # active -> handler runs


@dataclass(frozen=True)
class GateRun:
    """Observable result of one gated hook dispatch (port-exposed)."""

    gate_outcome: GateOutcome
    handler_stdin: str | None  # bytes the handler actually read (rewind proof)
    exit_code: int


def run_gate(*, envelope: Any, project_root: Path, global_config_path: Path) -> GateRun:
    """Run the activation gate over one hook envelope.

    Args:
        envelope: a hook envelope exposing ``raw`` (the literal stdin, or None).
        project_root: resolved project root sandbox.
        global_config_path: sandbox global-config path.

    Returns:
        ``GateRun`` with the observable gate outcome, the handler's stdin view
        (byte-identical to what the gate buffered), and the exit code (always 0;
        never 2 from the gate).
    """
    handler_stdin = envelope.raw  # buffered stdin, re-injected verbatim (DDD-6)

    if _is_active(project_root, global_config_path):
        return GateRun(GateOutcome.DISPATCHED, handler_stdin, 0)

    return GateRun(GateOutcome.ALLOWED_EXIT_0, handler_stdin, 0)


def apply_gate(command: str, stdin_text: str) -> str | None:
    """Production gate over real stdin for the in-process dispatch.

    Returns the re-injectable stdin text when the command should dispatch (the
    caller re-injects it as ``sys.stdin`` and runs the handler), or calls
    ``sys.exit(0)`` when the project is inactive (allow without blocking).
    Fail-open: any read/parse problem resolves to inactive under the default
    and exits 0.
    """
    # Missing/invalid cwd in the envelope falls back to the process cwd (Claude
    # Code always invokes hooks inside the project dir); resolution then runs
    # normally and only silences genuinely inactive projects.
    project_root = _parse_cwd(stdin_text) or resolve_nwave_root()
    if _is_active_or_inactive_on_error(project_root):
        return stdin_text

    sys.exit(0)


# ---------------------------------------------------------------------------
# gate helpers (no test-domain imports; duck-typed envelope access)
# ---------------------------------------------------------------------------


def _is_active(project_root: Path, global_config_path: Path) -> bool:
    config = NWaveConfig(cwd=project_root, global_config_path=global_config_path)
    return resolve_activation(config.enabled_for_repo, config.activation_mode)


def _is_active_or_inactive_on_error(project_root: Path) -> bool:
    """Resolve activation without letting an I/O fault activate a project.

    The gate must never raise or block. If activation cannot be resolved, the
    non-invasive result is inactive: exit zero without running a mutating
    handler.
    """
    try:
        return _is_active(project_root, _global_config_path())
    except Exception:
        return False


def _parse_cwd(stdin_text: str) -> Path | None:
    try:
        data = json.loads(stdin_text)
    except (json.JSONDecodeError, TypeError):
        return None
    cwd = data.get("cwd") if isinstance(data, dict) else None
    return Path(cwd) if cwd else None


def _global_config_path() -> Path:
    """Resolve the hook's global authority through the selected nWave home.

    A hook is launched later by Claude, often with ``HOME`` naming the
    machine account while ``NWAVE_AGENTS_HOME`` names the install selected by
    the operator.  Re-resolving the same location carrier as the installer is
    therefore necessary for the live gate to observe ``nwave-ai mode``.
    A malformed location override remains fail-to-inactive: this helper raises
    into the gate's existing error boundary, which suppresses dispatch.
    """
    result = NWaveLocations.resolve(
        home=Path.home(),
        repo_root=Path.cwd(),
        agents_home_override=os.environ.get("NWAVE_AGENTS_HOME") or None,
        claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR") or None,
        codex_config_override=os.environ.get("CODEX_HOME") or None,
    )
    if isinstance(result, Failure):
        raise ValueError(result.error)
    return result.unwrap().agents_home / ".nwave" / "config.json"


def reinject_stdin(stdin_text: str) -> io.StringIO:
    """Wrap buffered stdin text so a handler can read it verbatim (DDD-6)."""
    return io.StringIO(stdin_text)


# ---------------------------------------------------------------------------
# PreToolUse handler (verbatim from the removed pre_tool_use_handler; the
# git-stash guard, host scan and attribution mutation live in their homes)
# ---------------------------------------------------------------------------


def handle_pre_tool_use() -> int:
    """Handle PreToolUse command: validate Task tool invocation.

    Protocol translation only -- all decisions delegated to the guard, the
    host-scan limit and the attribution mutation in their own modules.

    Returns:
        0 if validation passes (allow)
        1 if error occurs (fail-closed)
        2 if validation fails (block)
    """
    hook_id = str(uuid.uuid4())
    start_ns = time.perf_counter_ns()
    exit_code = 0
    task_correlation_id: str | None = None
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            stdin_result = read_and_parse_stdin("pre_tool_use")

            if stdin_result.is_empty:
                return 0

            if stdin_result.parse_error:
                response = {"status": "error", "reason": stdin_result.parse_error}
                print(json.dumps(response))
                exit_code = 1
                return exit_code

            # The is_empty / parse_error guards above guarantee a parsed dict.
            hook_input = stdin_result.hook_input
            assert hook_input is not None  # narrowed by the guards above

            # Diagnostic: confirm hook was invoked
            tool_input = hook_input.get("tool_input", {})

            tool_name = hook_input.get("tool_name")

            # K4 architecture gap: nWave subagent host-scan lockdown. Cheap
            # for the overwhelming majority of Bash calls (non-find/bfs
            # commands, or a non-nWave-subagent caller) -- `_is_nwave_subagent`
            # is a dict-get + prefix check, no I/O.
            if tool_name == "Bash" and _is_nwave_subagent(hook_input):
                host_scan_block = _evaluate_nwave_subagent_host_scan(
                    tool_input.get("command")
                )
                if host_scan_block is not None:
                    print(json.dumps(host_scan_block))
                    exit_code = 2
                    return exit_code

            if hook_input.get("tool_name") == "Bash":
                # The git-stash safety decision already ran once,
                # pre-activation, in the dispatch (before `apply_gate`) -- see
                # `apply_bash_safety_guards`. Do not re-run it here; that would
                # be a duplicate second evaluation of the same command on the
                # active path.
                mutation_cwd = None
                if isinstance(hook_input.get("cwd"), str):
                    cwd_str = hook_input.get("cwd")
                    if cwd_str:
                        mutation_cwd = Path(cwd_str)
                mutation_exit = emit_commit_attribution_mutation(
                    tool_input, cwd=mutation_cwd
                )
                if mutation_exit is not None:
                    exit_code = mutation_exit
                    return exit_code
            log_hook_invoked(
                "pre_tool_use",
                {
                    "subagent_type": tool_input.get("subagent_type"),
                },
                hook_id=hook_id,
            )

            exit_code = 0
            return exit_code

    except Exception as e:
        # Fail-closed: any error blocks execution
        stderr_capture = stderr_buffer.getvalue()[:STDERR_CAPTURE_MAX_CHARS]
        log_hook_error("pre_tool_use", e, stderr_capture)
        response = {"status": "error", "reason": f"Unexpected error: {e!s}"}
        print(json.dumps(response))
        exit_code = 1
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = EXIT_CODE_TO_DECISION.get(exit_code, "error")
        log_hook_completed(
            HookCompletion(
                hook_id=hook_id,
                handler="pre_tool_use",
                exit_code=exit_code,
                decision=decision_str,
                duration_ms=duration_ms,
            ),
            TaskAccounting(task_correlation_id=task_correlation_id),
        )


# ---------------------------------------------------------------------------
# PreWrite/PreEdit handler (verbatim from the removed pre_write_handler)
# ---------------------------------------------------------------------------


def _log_pre_write_decision(
    hook_id: str,
    event_type: str,
    file_path: str,
    reason: str,
) -> None:
    """Log a HOOK_PRE_WRITE_ALLOWED or HOOK_PRE_WRITE_BLOCKED diagnostic event."""
    try:
        audit_writer = get_audit_writer()
        audit_writer.log_event(
            AuditEvent(
                event_type=event_type,
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data={
                    "hook_id": hook_id,
                    "file_path": file_path,
                    "reason": reason,
                },
            )
        )
    except Exception:
        pass  # Diagnostic logging must never break the hook


def handle_pre_write() -> int:
    """Handle PreToolUse for Write/Edit."""
    hook_id = str(uuid.uuid4())
    start_ns = time.perf_counter_ns()
    exit_code = 0
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            stdin_result = read_and_parse_stdin(
                "pre_write",
                json_error_fallback="allow",
            )

            if stdin_result.is_empty:
                return 0

            if stdin_result.parse_error:
                # Write/Edit fails open on parse errors
                return 0

            hook_input = stdin_result.hook_input

            # Extract file path from tool_input
            tool_input = hook_input.get("tool_input", {})
            file_path = tool_input.get("file_path", "")

            # --- Execution log guard: always block direct writes ---
            if file_path and file_path.endswith("execution-log.json"):
                block_reason = (
                    "execution-log.json belongs to a retired workflow and cannot be "
                    "created or modified.\n\n"
                    "Use the current atdd_pure delivery inputs: the selected feature "
                    "delta and its acceptance tests. Do not recreate retired phase records."
                )
                _log_pre_write_decision(
                    hook_id=hook_id,
                    event_type="HOOK_PRE_WRITE_BLOCKED",
                    file_path=file_path,
                    reason="execution_log_direct_write",
                )
                print(json.dumps({"decision": "block", "reason": block_reason}))
                return 2

            # --- Lane guard: a sub-agent never writes the root checkout while lanes are live ---
            lane_refusal = lane_guard.root_checkout_write_refusal(
                file_path,
                str(hook_input.get("cwd") or ""),
                hook_input.get("agent_type"),
                lane_guard.live_lanes(Path(str(hook_input.get("cwd") or "."))),
            )
            if lane_refusal:
                _log_pre_write_decision(
                    hook_id=hook_id,
                    event_type="HOOK_PRE_WRITE_BLOCKED",
                    file_path=file_path,
                    reason="root_checkout_write_from_sub_agent",
                )
                print(json.dumps({"decision": "block", "reason": lane_refusal}))
                return 2

            log_hook_invoked(
                "pre_write",
                {
                    "file_path": file_path,
                    "des_task_active": DES_TASK_ACTIVE_FILE.exists(),
                },
                hook_id=hook_id,
            )
            _log_pre_write_decision(
                hook_id=hook_id,
                event_type="HOOK_PRE_WRITE_ALLOWED",
                file_path=file_path,
                reason="ordinary_write",
            )
            exit_code = 0
            return exit_code

    except Exception as e:
        # Fail-open for Write/Edit (unlike Task which is fail-closed)
        stderr_capture = stderr_buffer.getvalue()[:STDERR_CAPTURE_MAX_CHARS]
        log_hook_error(
            "pre_write",
            e,
            stderr_capture,
        )
        exit_code = 0
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = EXIT_CODE_TO_DECISION.get(exit_code, "error")
        log_hook_completed(
            HookCompletion(
                hook_id=hook_id,
                handler="pre_write",
                exit_code=exit_code,
                decision=decision_str,
                duration_ms=duration_ms,
            )
        )


# ---------------------------------------------------------------------------
# SubagentStop handler (verbatim from the removed subagent_stop_handler)
# ---------------------------------------------------------------------------

_NWAVE_AGENT_PREFIX = "nw-"


def _resolve_agent_type(agent_type: str, transcript_path: str | None) -> str:
    """The role this subagent actually played, not the label it was dispatched under.

    For an UNNAMED Agent-tool dispatch the platform's ``agent_type`` already
    IS the role (``nw-troubleshooter-reviewer``). For a NAMED in-process
    teammate it is the LANE NAME (``speedfix``): Claude Code 2.1.239's own
    in-process-teammate agent definition sets ``agentType: t.agentName`` and
    stashes the real role separately as ``customAgentType`` in the teammate
    metadata; the SubagentStop hookInput's ``agent_type`` is sourced from the
    former. A bare ``startswith("nw-")`` gate therefore silently no-ops for
    every named nWave lane -- exactly the silence this resolution exists to
    close, so cleanup below still fires for a named lane's real nw-* role.

    The role is recovered from the sidecar the platform writes beside the
    transcript it hands us in ``agent_transcript_path``
    (``<transcript-stem>.meta.json``). Fail-open: an absent, unreadable,
    non-JSON or roleless sidecar yields ``""`` -- a no-op, never a guess.
    """
    if agent_type.startswith(_NWAVE_AGENT_PREFIX):
        return agent_type
    if not transcript_path:
        return ""
    try:
        sidecar = Path(transcript_path).with_suffix(".meta.json")
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    custom = meta.get("customAgentType") if isinstance(meta, dict) else None
    if isinstance(custom, str) and custom.startswith(_NWAVE_AGENT_PREFIX):
        return custom
    return ""


def _run_cleanup(transcript_path: str | None) -> None:
    """Wires the two previously-orphaned, correctly-shaped SubagentStop
    consumers an earlier inventory pass named: the task-signal removal
    (``nwave_ai.hooks.run_context.remove_signal``: "Remove signal when
    SubagentStop fires") and skill-load tracking
    (``nwave_ai.hooks.skill_tracking.maybe_track_skill_loads``). Both are
    already fail-open internally; this wraps them again defensively so a
    future regression in either can never reach this handler's own
    fail-open contract."""
    try:
        _remove_task_signal()
    except Exception:
        pass
    if transcript_path:
        try:
            maybe_track_skill_loads(transcript_path)
        except Exception:
            pass


def handle_subagent_stop() -> int:
    """Handle subagent-stop hook: run cleanup for a resolved nWave agent.

    Reads JSON from stdin (Claude Code SubagentStop hook protocol). For
    non-nWave agents (`agent_type` absent, empty, not `nw-`-prefixed even
    after named-teammate resolution): no-op, exit 0. For nWave agents: runs
    `_run_cleanup` (task-signal removal, skill-load tracking) and exits 0.

    Returns:
        0 always (fail-open: a hook firing during a subagent's own
        termination must never itself raise or block).
    """
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw)
    except Exception:
        return 0

    try:
        agent_type = hook_input.get("agent_type") or ""
        if not isinstance(agent_type, str):
            return 0

        transcript_path = hook_input.get("agent_transcript_path")
        transcript_path = transcript_path if isinstance(transcript_path, str) else None

        agent_type = _resolve_agent_type(agent_type, transcript_path)
        if not agent_type:
            return 0

        _run_cleanup(transcript_path)
        return 0
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# In-process dispatch (verbatim from the removed hook_router main)
# ---------------------------------------------------------------------------


def _route(command: str, host: str) -> None:
    """Route one resolved handler action to its handler; exits the process."""
    command = command.replace("_", "-")

    # Activation gate (ADR-AG-001): buffer stdin at the top, before any handler
    # reads it, so the gate can resolve the project and re-inject the bytes
    # byte-identically. Inactive commands exit 0 (allow, never block) inside
    # apply_gate. The read is defensive (fail-open): an unreadable stdin yields
    # an empty buffer.
    try:
        buffered_stdin = sys.stdin.read()
    except (OSError, ValueError):
        buffered_stdin = ""

    # ADR-AG-001 ordering repair: the git-stash safety decision must run BEFORE
    # the activation gate, else an inactive project exits 0 inside apply_gate
    # before this safety check ever runs. Evaluated exactly once here;
    # `handle_pre_tool_use` no longer re-runs it.
    safety_stdin = normalize_exec_command_envelope(command, buffered_stdin)
    apply_bash_safety_guards(command, safety_stdin)

    # Global activity registry: every host session is recorded BEFORE the
    # activation gate, because the installation an update replaces is shared
    # by inactive projects too. SessionEnd needs nothing else and exits here.
    if command == "session-end":
        sys.exit(handle_session_end(buffered_stdin, host))
    registration = None
    if command == "session-start":
        registration = register_session_start(buffered_stdin, host)
        if not registration.admitted:
            # Safety warnings must survive inactive projects and unavailable
            # route notices. Exit 0 is advisory, never proof the host is gated.
            sys.exit(emit_admission_warning(registration))

    reinjected = apply_gate(command, buffered_stdin)
    sys.stdin = io.StringIO(reinjected if reinjected is not None else buffered_stdin)

    # Freshness is relevant only after explicit project activation. Running it
    # at facade import time created `.nwave/des/logs` before the activation gate
    # could silence an unrelated repository.
    assert_fresh_or_explain(suppress_git_autoskip=True)

    if command in ("pre-tool-use", "pre-task"):
        # "pre-task" accepted for backward compatibility
        exit_code = handle_pre_tool_use()
    elif command in ("pre-write", "pre-edit"):
        exit_code = handle_pre_write()
    elif command == "subagent-stop":
        exit_code = handle_subagent_stop()
    elif command == "session-start":
        exit_code = handle_session_start(registration)
    else:
        print(json.dumps({"status": "error", "reason": f"Unknown command: {command}"}))
        exit_code = 1

    sys.exit(exit_code)


def main(argv: list[str] | None = None) -> None:
    """Hook entry point: parse the kept registration's event and host, resolve
    the handler action, and run it in-process."""
    parser = argparse.ArgumentParser(prog="nwave_ai.hooks")
    parser.add_argument("event", choices=EVENTS)
    parser.add_argument("--host", required=True, choices=HOSTS)
    args = parser.parse_args(argv)
    payload = sys.stdin.read()
    sys.stdin = io.StringIO(payload)
    host = "codex" if args.host == "codex" else "claude-code"
    _route(action_for(args.event, payload), host)


if __name__ == "__main__":
    main()
