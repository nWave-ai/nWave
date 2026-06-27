"""PreToolUse handler — validates Task/Agent tool invocations.

Translates Claude Code's PreToolUse hook event (JSON stdin) into
PreToolUseService decisions (allow/block), manages DES task signal creation,
and emits audit events through hook_protocol.

Extracted from claude_code_hook_adapter.py as part of P4 decomposition.
"""

import contextlib
import io
import json
import time
import uuid
from pathlib import Path

from des.adapters.drivers.hooks import des_task_signal, service_factory
from des.adapters.drivers.hooks.hook_protocol import (
    EXIT_CODE_TO_DECISION,
    STDERR_CAPTURE_MAX_CHARS,
    log_hook_completed,
    log_hook_error,
    log_hook_invoked,
    read_and_parse_stdin,
)
from des.application.commit_attribution_service import CommitAttributionService
from des.domain.des_marker_parser import DesMarkerParser
from des.ports.driver_ports.pre_tool_use_port import PreToolUseInput


def emit_commit_attribution_mutation(tool_input: dict[str, object]) -> int | None:
    """Net-new mutation branch: rewrite a Bash `git commit` to carry the trailer.

    ADR-CA-006 D4 (Reuse row R4). On a Bash `git commit` command, asks
    :class:`CommitAttributionService` for a :class:`CommitRewritePlan`. On a
    mutate Plan, emits the protocol JSON
    ``{"hookSpecificOutput":{"hookEventName":"PreToolUse",
    "permissionDecision":"allow","updatedInput":{<full tool_input, command
    rewritten>}}}`` on stdout and returns exit 0. On a passthrough Plan, returns
    ``None`` so the caller falls through to the existing validation path
    unchanged.

    This is the ONLY net-new branch in the handler; the existing block/allow
    validation path is not modified.

    Args:
        tool_input: the ``tool_input`` object from the PreToolUse payload. Its
            ``command`` field is the Bash command to consider.

    Returns:
        ``0`` after emitting a mutation; ``None`` to fall through to the existing
        validation path (passthrough / non-Bash / non-commit).
    """
    command = tool_input.get("command")
    if not isinstance(command, str) or not command:
        return None

    # Fail-safe (ADR-CA-006): attribution is best-effort. ANY error here — a
    # raising rewrite core, a JSON-serialization failure — must NOT propagate to
    # the outer `handle_pre_tool_use` `except Exception`, which fail-closes to
    # exit 1 and BLOCKS the commit. A missed trailer is recoverable; a blocked
    # commit is not. On any failure, return None so the caller falls through to
    # the existing validation path and the original command runs unchanged.
    try:
        plan = _commit_attribution_service.plan_rewrite(command)
        if plan.action != "mutate" or plan.rewritten_command is None:
            return None

        updated_input = {**tool_input, "command": plan.rewritten_command}
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": updated_input,
                    }
                }
            )
        )
        return 0
    except Exception:
        return None


# Bound so step-composition / future wiring reference a single seam, not a free
# constructor call. DELIVER injects the real service here.
_commit_attribution_service = CommitAttributionService()


def _resolve_deliverable_type() -> str | None:
    """Resolve the project deliverable type for this dispatch (ADR-PST-001).

    Reads ``DESConfig(cwd=Path.cwd()).deliverable_type`` over the dispatch's
    working directory: a plugin/skill declaration on disk threads through
    ``service_factory`` into ``PreToolUseService.validate`` and exempts the
    step dispatch. An unresolved/absent/``application`` project returns ``None``
    so enforcement stays ON (fail-safe by construction).
    """
    from des.adapters.driven.config.des_config import DESConfig

    return DESConfig(cwd=Path.cwd()).deliverable_type


def handle_pre_tool_use() -> int:
    """Handle PreToolUse command: validate Task tool invocation.

    Protocol translation only -- all decisions delegated to PreToolUseService.

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

            hook_input = stdin_result.hook_input or {}

            # Diagnostic: confirm hook was invoked
            tool_input = hook_input.get("tool_input", {})

            # NET-NEW mutation branch (ADR-CA-006 D4) — reached from the REAL
            # entry point so the seam is not dormant (Mandate 15 / S3). Only
            # Bash tool invocations are candidates for commit-attribution
            # rewriting; everything else falls through unchanged to the existing
            # validation path below. DISTILL scaffold: the branch helper raises
            # AssertionError (RED) until DELIVER implements it.
            if hook_input.get("tool_name") == "Bash":
                mutation_exit = emit_commit_attribution_mutation(tool_input)
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

            # Extract protocol fields
            # Claude Code sends: {"tool_name": "Agent", "tool_input": {...}, ...}
            prompt = tool_input.get("prompt", "")

            # Resolve the project deliverable type (ADR-PST-001, feature
            # plugin-skill-deliverable-type) and thread it into the service so
            # the enforcement policy can exempt plugin/skill projects. This is
            # the handler SEAM the driving-adapter acceptance scenario drives.
            deliverable_type = _resolve_deliverable_type()

            # Delegate to application service
            service = service_factory.create_pre_tool_use_service(
                deliverable_type=deliverable_type
            )
            decision = service.validate(
                PreToolUseInput(
                    prompt=prompt,
                    subagent_type=tool_input.get("subagent_type"),
                ),
                hook_id=hook_id,
            )

            # Translate HookDecision to protocol response
            if decision.action == "allow":
                # Create DES task signal if this is a DES-validated task
                if "DES-VALIDATION" in prompt:
                    # Extract step-id and project-id from DES markers
                    step_id_marker = ""
                    project_id_marker = ""
                    parser = DesMarkerParser()
                    markers = parser.parse(prompt)
                    if markers.step_id:
                        step_id_marker = markers.step_id
                    if markers.project_id:
                        project_id_marker = markers.project_id
                    task_correlation_id = des_task_signal.create_signal(
                        step_id=step_id_marker, project_id=project_id_marker
                    )
                exit_code = 0
                return exit_code
            else:
                recovery = decision.recovery_suggestions or []
                reason_with_recovery = decision.reason or "Validation failed"
                if recovery:
                    reason_with_recovery += "\n\nRecovery:\n" + "\n".join(
                        f"  {i + 1}. {s}" for i, s in enumerate(recovery)
                    )
                response = {
                    "decision": "block",
                    "reason": reason_with_recovery,
                }
                print(json.dumps(response))
                exit_code = decision.exit_code
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
            hook_id=hook_id,
            handler="pre_tool_use",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
            task_correlation_id=task_correlation_id,
        )
