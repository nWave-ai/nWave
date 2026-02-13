"""SubagentStopService - application service for step completion validation.

Orchestrates domain logic (StepCompletionValidator) and driven ports
(ExecutionLogReader, ScopeChecker, AuditLogWriter, TimeProvider) to produce
allow/block decisions for step completion.

This service implements the SubagentStopPort driver port interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driven_ports.execution_log_reader import (
    ExecutionLogReader,
    LogFileCorrupted,
    LogFileNotFound,
)
from des.ports.driver_ports.pre_tool_use_port import HookDecision
from des.ports.driver_ports.subagent_stop_port import (
    SubagentStopContext,
    SubagentStopPort,
)


if TYPE_CHECKING:
    from des.domain.log_integrity_validator import (
        CorrectableEntry,
        LogIntegrityValidator,
    )
    from des.domain.step_completion_validator import StepCompletionValidator
    from des.ports.driven_ports.commit_verifier import (
        CommitVerificationResult,
        CommitVerifier,
    )
    from des.ports.driven_ports.scope_checker import ScopeChecker
    from des.ports.driven_ports.time_provider_port import TimeProvider


class SubagentStopService(SubagentStopPort):
    """Validates step completion when a subagent finishes.

    Flow:
      1. Read project_id via ExecutionLogReader.read_project_id()
         - If not found: return block (LOG_FILE_NOT_FOUND)
         - If mismatch: return block (PROJECT_ID_MISMATCH)
      2. Read step events via ExecutionLogReader.read_step_events()
      3. Validate completion via StepCompletionValidator.validate()
         - If invalid: log HOOK_SUBAGENT_STOP_FAILED, return block
      3.5. Verify git commit via CommitVerifier (if cwd provided)
         - If no matching commit: return block (COMMIT_NOT_VERIFIED)
         - Fail-closed: git errors also block
      4. Check scope via ScopeChecker.check_scope()
         - If violations: log SCOPE_VIOLATION (warning, does not block)
      5. Log HOOK_SUBAGENT_STOP_PASSED, return allow
    """

    def __init__(
        self,
        log_reader: ExecutionLogReader,
        completion_validator: StepCompletionValidator,
        scope_checker: ScopeChecker,
        audit_writer: AuditLogWriter,
        time_provider: TimeProvider,
        commit_verifier: CommitVerifier | None = None,
        integrity_validator: LogIntegrityValidator | None = None,
    ) -> None:
        self._log_reader = log_reader
        self._completion_validator = completion_validator
        self._scope_checker = scope_checker
        self._audit_writer = audit_writer
        self._time_provider = time_provider
        self._commit_verifier = commit_verifier
        self._integrity_validator = integrity_validator

    def validate(
        self,
        context: SubagentStopContext,
        hook_id: str | None = None,
    ) -> HookDecision:
        """Validate step completion for a subagent.

        Args:
            context: Parsed context from the hook protocol
            hook_id: Optional correlation ID from the adapter hook invocation.
                When provided, included in all emitted audit events for correlation.

        Returns:
            HookDecision indicating allow or block
        """
        # Step 1: Read and validate project_id
        try:
            log_project_id = self._log_reader.read_project_id(
                context.execution_log_path
            )
        except LogFileNotFound:
            return HookDecision.block(
                reason=f"Execution log not found: {context.execution_log_path}",
                recovery_suggestions=[
                    "Create execution-log.yaml file",
                    "Run orchestrator to initialize log",
                ],
            )
        except LogFileCorrupted as e:
            return HookDecision.block(
                reason=f"Invalid YAML in execution log: {e}",
                recovery_suggestions=["Fix YAML syntax errors in execution-log.yaml"],
            )

        if log_project_id != context.project_id:
            return HookDecision.block(
                reason=f"Project ID mismatch: expected '{context.project_id}', found '{log_project_id}'",
                recovery_suggestions=[
                    f"Verify you're working on project '{context.project_id}'",
                    "Check DES-PROJECT-ID marker in prompt",
                ],
            )

        # Step 2: Read step events
        try:
            events = self._log_reader.read_step_events(
                context.execution_log_path,
                context.step_id,
            )
        except (LogFileNotFound, LogFileCorrupted) as e:
            return HookDecision.block(
                reason=f"Failed to read step events: {e}",
                recovery_suggestions=["Check execution-log.yaml file integrity"],
            )

        # Step 2.5: Check and correct log integrity (BEFORE completion check)
        # Runs always, even on retry -- correction is better than blocking
        self._check_and_correct_integrity(context)

        # Re-read events after potential correction so completion validates
        # against corrected timestamps
        try:
            events = self._log_reader.read_step_events(
                context.execution_log_path,
                context.step_id,
            )
        except (LogFileNotFound, LogFileCorrupted):
            pass  # Use original events if re-read fails

        # Step 3: Validate completion
        completion = self._completion_validator.validate(events)

        if not completion.is_valid:
            error_parts = list(completion.error_messages)
            error_message = (
                "; ".join(error_parts) if error_parts else "Validation failed"
            )

            if context.stop_hook_active:
                # Second attempt: allow to prevent infinite loop, but still log FAILED
                self._log_failed(
                    context.project_id,
                    context.step_id,
                    error_parts,
                    allowed_despite_failure=True,
                    hook_id=hook_id,
                    turns_used=context.turns_used,
                    tokens_used=context.tokens_used,
                )
                return HookDecision.allow()

            # First attempt: block so sub-agent can try to fix
            self._log_failed(
                context.project_id,
                context.step_id,
                error_parts,
                hook_id=hook_id,
                turns_used=context.turns_used,
                tokens_used=context.tokens_used,
            )
            return HookDecision.block(
                reason=error_message,
                recovery_suggestions=completion.recovery_suggestions,
            )

        # Step 3.5: Verify git commit exists (only if phases passed and cwd provided)
        if context.cwd and self._commit_verifier:
            commit_result = self._commit_verifier.verify_commit(
                context.step_id, context.cwd
            )
            if not commit_result.verified:
                self._log_commit_not_verified(context, commit_result, hook_id=hook_id)
                return HookDecision.block(
                    reason=f"COMMIT_NOT_VERIFIED: {commit_result.error_reason}",
                    recovery_suggestions=[
                        f"Create a git commit with trailer 'Step-ID: {context.step_id}'",
                        "Ensure the COMMIT phase actually runs git commit",
                        "Check that git is available and you're in a git repository",
                    ],
                )
            self._log_commit_verified(context, commit_result, hook_id=hook_id)

        # Step 4: Check scope (warning only, does not block)
        self._check_and_log_scope(context)

        # Step 5: All valid
        self._log_passed(
            context.project_id,
            context.step_id,
            hook_id=hook_id,
            turns_used=context.turns_used,
            tokens_used=context.tokens_used,
        )
        return HookDecision.allow()

    def _check_and_correct_integrity(self, context: SubagentStopContext) -> None:
        """Check log integrity and correct fabricated timestamps (zero trust).

        Runs BEFORE stop_hook_active check -- correction always happens.
        Only corrects events for context.step_id written during task window.
        """
        if not self._integrity_validator:
            return

        try:
            all_events = self._log_reader.read_all_events(
                context.execution_log_path,
            )
        except (LogFileNotFound, LogFileCorrupted):
            return

        result = self._integrity_validator.validate(
            step_id=context.step_id,
            all_events=all_events,
            task_start_time=context.task_start_time or None,
        )

        # Correct fabricated timestamps; track which were actually corrected
        corrected_entries: set[int] = set()
        if result.correctable_entries:
            corrected_entries = self._correct_timestamps(
                context, result.correctable_entries
            )

        # Log remaining warnings (non-correctable issues like phase name typos)
        for warning in result.warnings:
            # Skip warnings that correspond to actually corrected entries
            is_corrected = any(
                entry.index in corrected_entries
                and entry.phase_name in warning
                and entry.original_timestamp in warning
                for entry in result.correctable_entries
            )
            if not is_corrected:
                self._audit_writer.log_event(
                    AuditEvent(
                        event_type="LOG_INTEGRITY_WARNING",
                        timestamp=self._time_provider.now_utc().isoformat(),
                        feature_name=context.project_id,
                        step_id=context.step_id,
                        data={"warning": warning},
                    )
                )

    def _correct_timestamps(
        self,
        context: SubagentStopContext,
        correctable: list[CorrectableEntry],
    ) -> set[int]:
        """Rewrite fabricated timestamps with interpolated real ones.

        Interpolation: distributes N timestamps evenly between task_start
        and now(), preserving phase ordering.

        Returns:
            Set of entry indices that were actually corrected.
        """
        from datetime import datetime, timezone

        import yaml

        corrected_indices: set[int] = set()

        # Determine time window
        now = self._time_provider.now_utc()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if context.task_start_time:
            try:
                start = datetime.fromisoformat(context.task_start_time)
            except (ValueError, TypeError):
                start = now
        else:
            start = now

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        # Calculate interpolated timestamps
        n = len(correctable)
        if n == 1:
            # Single entry: place at midpoint
            delta = (now - start) / 2
            interpolated = [start + delta]
        else:
            # Multiple entries: distribute evenly
            step = (now - start) / (n + 1)
            interpolated = [start + step * (i + 1) for i in range(n)]

        # Read raw YAML
        try:
            log_path = Path(context.execution_log_path)
            raw_yaml = yaml.safe_load(log_path.read_text())
        except Exception:
            return corrected_indices

        raw_events = raw_yaml.get("events", [])

        # Replace timestamps in raw event strings
        for entry, new_ts in zip(correctable, interpolated, strict=False):
            if entry.index < len(raw_events):
                old_event_str = raw_events[entry.index]
                if (
                    isinstance(old_event_str, str)
                    and entry.original_timestamp in old_event_str
                ):
                    new_ts_str = new_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
                    raw_events[entry.index] = old_event_str.replace(
                        entry.original_timestamp, new_ts_str
                    )
                    corrected_indices.add(entry.index)

                    # Log correction audit event
                    self._audit_writer.log_event(
                        AuditEvent(
                            event_type="LOG_INTEGRITY_CORRECTED",
                            timestamp=self._time_provider.now_utc().isoformat(),
                            feature_name=context.project_id,
                            step_id=context.step_id,
                            data={
                                "phase": entry.phase_name,
                                "original_timestamp": entry.original_timestamp,
                                "corrected_timestamp": new_ts_str,
                                "reason": entry.reason,
                            },
                        )
                    )

        # Write corrected YAML back
        try:
            raw_yaml["events"] = raw_events
            log_path.write_text(
                yaml.dump(raw_yaml, default_flow_style=False, sort_keys=False)
            )
        except Exception:
            pass  # Correction is best-effort

        return corrected_indices

    def _check_and_log_scope(self, context: SubagentStopContext) -> None:
        """Check scope violations and log warnings."""
        log_path = Path(context.execution_log_path)
        # execution-log.yaml is in docs/feature/{project}/
        project_root = log_path.parent.parent.parent

        scope_result = self._scope_checker.check_scope(
            project_root=project_root,
            # TODO: Extract allowed patterns from roadmap.yaml
            allowed_patterns=["**/*"],
        )

        if scope_result.has_violations:
            for file_path in scope_result.out_of_scope_files:
                self._audit_writer.log_event(
                    AuditEvent(
                        event_type="SCOPE_VIOLATION",
                        timestamp=self._time_provider.now_utc().isoformat(),
                        feature_name=context.project_id,
                        step_id=context.step_id,
                        data={
                            "out_of_scope_file": file_path,
                        },
                    )
                )

    @staticmethod
    def _add_execution_stats(
        data: dict,
        turns_used: int | None,
        tokens_used: int | None,
    ) -> None:
        """Add turns_used and tokens_used to event data dict when present.

        Centralizes the repeated conditional insertion of execution statistics
        into audit event data across _log_passed, _log_failed, and
        _log_commit_verified.

        Args:
            data: Mutable event data dict to enrich in place.
            turns_used: Number of turns used by the subagent, or None.
            tokens_used: Number of tokens used by the subagent, or None.
        """
        if turns_used is not None:
            data["turns_used"] = turns_used
        if tokens_used is not None:
            data["tokens_used"] = tokens_used

    def _log_passed(
        self,
        feature_name: str,
        step_id: str,
        hook_id: str | None = None,
        turns_used: int | None = None,
        tokens_used: int | None = None,
    ) -> None:
        """Log successful validation to the audit trail."""
        data: dict = {}
        self._add_execution_stats(data, turns_used, tokens_used)
        self._audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_SUBAGENT_STOP_PASSED",
                timestamp=self._time_provider.now_utc().isoformat(),
                feature_name=feature_name,
                step_id=step_id,
                hook_id=hook_id,
                data=data,
            )
        )

    def _log_failed(
        self,
        feature_name: str,
        step_id: str,
        error_messages: list[str],
        allowed_despite_failure: bool = False,
        hook_id: str | None = None,
        turns_used: int | None = None,
        tokens_used: int | None = None,
    ) -> None:
        """Log failed validation to the audit trail."""
        data: dict = {
            "validation_errors": error_messages,
        }
        if allowed_despite_failure:
            data["allowed_despite_failure"] = True
        self._add_execution_stats(data, turns_used, tokens_used)
        self._audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_SUBAGENT_STOP_FAILED",
                timestamp=self._time_provider.now_utc().isoformat(),
                feature_name=feature_name,
                step_id=step_id,
                hook_id=hook_id,
                data=data,
            )
        )

    def _log_commit_verified(
        self,
        context: SubagentStopContext,
        result: CommitVerificationResult,
        hook_id: str | None = None,
    ) -> None:
        """Log successful commit verification to the audit trail."""
        data: dict = {
            "commit_hash": result.commit_hash,
            "commit_date": result.commit_date,
            "commit_subject": result.commit_subject,
        }
        self._add_execution_stats(data, context.turns_used, context.tokens_used)
        self._audit_writer.log_event(
            AuditEvent(
                event_type="COMMIT_VERIFIED",
                timestamp=self._time_provider.now_utc().isoformat(),
                feature_name=context.project_id,
                step_id=context.step_id,
                hook_id=hook_id,
                data=data,
            )
        )

    def _log_commit_not_verified(
        self,
        context: SubagentStopContext,
        result: CommitVerificationResult,
        hook_id: str | None = None,
    ) -> None:
        """Log failed commit verification to the audit trail."""
        self._audit_writer.log_event(
            AuditEvent(
                event_type="COMMIT_NOT_VERIFIED",
                timestamp=self._time_provider.now_utc().isoformat(),
                feature_name=context.project_id,
                step_id=context.step_id,
                hook_id=hook_id,
                data={
                    "error_reason": result.error_reason,
                },
            )
        )
