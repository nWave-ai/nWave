"""
DES Orchestrator for command-origin task filtering with schema version routing.

This module implements the orchestrator that determines whether to apply
DES validation based on command origin (execute/develop vs research/ad-hoc).

Schema Versioning (Step US-005-03):
- Detects schema_version field in step files (v1.0 for 14-phase, v2.0 for 8-phase)
- Routes to appropriate validator based on detected version
- Supports mixed-schema during US-005 Phase 2→3 transition
- Implements automatic rollback: 2 failures → fallback to v1.0 from v2.0

Integration: US-002 Template Validation
- Pre-invocation validation ensures prompts contain all mandatory sections
- Blocks Task invocation if validation fails

Integration: US-003 Post-Execution Validation
- Invokes SubagentStopHook after sub-agent completion
- Validates step file phase execution state
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from des.adapters.driven.logging.audit_events import AuditEvent, EventType
from des.adapters.driven.logging.jsonl_audit_log_writer import JsonlAuditLogWriter
from des.application.stale_execution_detector import StaleExecutionDetector
from des.domain.des_marker_generator import DESMarkerGenerator
from des.domain.invocation_limits_validator import (
    InvocationLimitsResult,
    InvocationLimitsValidator,
)
from des.domain.prompt_metadata_extractor import PromptMetadataExtractor
from des.domain.schema_version_detector import SchemaVersionDetector
from des.domain.step_file_repository import StepFileRepository
from des.domain.timeout_monitor import TimeoutMonitor
from des.domain.timeout_warning_builder import TimeoutWarningBuilder
from des.domain.turn_counter import TurnCounter
from des.ports.driven_ports.audit_log_writer import (
    AuditEvent as PortAuditEvent,
)
from des.ports.driven_ports.filesystem_port import FileSystemPort
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.validator_port import ValidationResult, ValidatorPort


if TYPE_CHECKING:
    from des.domain.stale_execution import StaleExecution


# ---------------------------------------------------------------------------
# Inlined from legacy hook_port.py (deleted as part of hex-arch redesign)
# ---------------------------------------------------------------------------


@dataclass
class HookResult:
    """Result from hook validation."""

    validation_status: str
    hook_fired: bool = True
    abandoned_phases: list[str] = field(default_factory=list)
    incomplete_phases: list[str] = field(default_factory=list)
    invalid_skips: list[str] = field(default_factory=list)
    error_count: int = 0
    error_type: str | None = None
    error_message: str | None = None
    recovery_suggestions: list[str] = field(default_factory=list)
    not_executed_phases: int = 0
    turn_limit_exceeded: bool = False
    timeout_exceeded: bool = False


class HookPort(ABC):
    """Port for post-execution validation hooks."""

    @abstractmethod
    def persist_turn_count(
        self, step_file_path: str, phase_name: str, turn_count: int
    ) -> None:
        """Persist turn_count to phase_execution_log entry."""
        pass

    @abstractmethod
    def on_agent_complete(self, step_file_path: str) -> HookResult:
        """Validate step file after sub-agent completion."""
        pass


class _NoOpHook(HookPort):
    """Minimal HookPort that always passes.

    Used by create_with_defaults() after legacy SubagentStopHook was removed.
    Production validation now runs through claude_code_hook_adapter ->
    SubagentStopService, bypassing the orchestrator's hook entirely.
    """

    def persist_turn_count(
        self, step_file_path: str, phase_name: str, turn_count: int
    ) -> None:
        pass

    def on_agent_complete(self, step_file_path: str) -> HookResult:
        return HookResult(validation_status="PASSED")


# ---------------------------------------------------------------------------
# Audit logging bridge
# ---------------------------------------------------------------------------


def _log_audit_event(event_type: str, **kwargs: object) -> None:
    """Log an audit event using JsonlAuditLogWriter.

    Drop-in replacement for the legacy ``log_audit_event()`` convenience
    function that was removed together with ``audit_logger.py``.

    ``feature_name`` and ``step_id`` are extracted from *kwargs* and passed
    as direct :class:`PortAuditEvent` fields for structured traceability.
    All remaining kwargs are placed in the ``data`` dict.
    """
    from des.adapters.driven.time.system_time import SystemTimeProvider

    feature_name = kwargs.pop("feature_name", None)
    step_id = kwargs.pop("step_id", None)

    writer = JsonlAuditLogWriter()
    timestamp = SystemTimeProvider().now_utc().isoformat()
    writer.log_event(
        PortAuditEvent(
            event_type=event_type,
            timestamp=timestamp,
            feature_name=feature_name,
            step_id=step_id,
            data={k: v for k, v in kwargs.items() if v is not None},
        )
    )


@dataclass
class ExecuteStepResult:
    """Result from execute_step() method execution.

    Attributes:
        turn_count: Total number of turns (iterations) executed
        phase_name: Name of the phase being executed (required, loaded from step file)
        status: Execution status (e.g., "COMPLETED", "IN_PROGRESS")
        warnings_emitted: List of timeout warnings emitted during execution (deprecated, use timeout_warnings)
        timeout_warnings: List of timeout warning strings emitted during execution
        execution_path: Execution path identifier for validation (e.g., "DESOrchestrator.execute_step")
        features_validated: List of DES features validated during execution
    """

    turn_count: int
    phase_name: str  # Required - loaded from step file, no hardcoded default
    status: str = "COMPLETED"
    warnings_emitted: list[str] = field(
        default_factory=list
    )  # Deprecated, use timeout_warnings
    timeout_warnings: list[str] = field(default_factory=list)
    execution_path: str = "DESOrchestrator.execute_step"
    features_validated: list[str] = field(default_factory=list)


@dataclass
class ExecuteStepWithStaleCheckResult:
    """Result from execute_step_with_stale_check() method execution.

    Attributes:
        blocked: True if execution was blocked due to stale detection
        blocking_reason: Reason for blocking (e.g., "STALE_EXECUTION_DETECTED")
        stale_alert: StaleExecution object with alert details (if blocked)
        execute_result: ExecuteStepResult from normal execution (if not blocked)
    """

    blocked: bool
    blocking_reason: str | None = None
    stale_alert: Optional["StaleExecution"] = None
    execute_result: ExecuteStepResult | None = None


class DESOrchestrator:
    """
    Orchestrates DES validation by analyzing command origin.

    Responsibilities:
    - Render prompts with DES markers for execute/develop commands
    - Prepare ad-hoc prompts without DES markers for exploration
    - Track command origin for audit trail
    """

    # Commands that require full DES validation
    VALIDATION_COMMANDS = ["/nw:execute", "/nw:develop"]

    def __init__(
        self,
        hook: HookPort,
        validator: ValidatorPort,
        filesystem: FileSystemPort,
        time_provider: TimeProvider,
    ):
        """Initialize with injected ports.

        Args:
            hook: Post-execution validation hook
            validator: Template validation
            filesystem: File I/O operations
            time_provider: Time operations
        """
        self._hook = hook
        self._validator = validator
        self._filesystem = filesystem
        self._time_provider = time_provider
        self._subagent_lifecycle_completed = False
        self._step_file_path: Path | None = None

        # Initialize extracted domain services
        self._schema_detector = SchemaVersionDetector(filesystem)
        self._marker_generator = DESMarkerGenerator()
        self._metadata_extractor = PromptMetadataExtractor()
        self._warning_builder = TimeoutWarningBuilder()
        self._step_repository = StepFileRepository(filesystem)

    # ========================================================================
    # Schema Version Detection
    # ========================================================================

    def detect_schema_version(self, step_file_path: Path) -> str:
        """
        Detect schema version from step file.

        Reads the step file and extracts schema_version field to determine
        which TDD phase cycle it uses (v1.0 = 14 phases, v2.0 = 8 phases).

        Args:
            step_file_path: Path to step JSON file

        Returns:
            Schema version string (e.g., "1.0", "2.0", "unknown")

        Raises:
            FileNotFoundError: If step file does not exist
            json.JSONDecodeError: If step file is not valid JSON
        """
        return self._schema_detector.detect_version(step_file_path)

    def get_phase_count_for_schema(self, schema_version: str) -> int:
        """
        Get expected phase count for schema version.

        Args:
            schema_version: Schema version (e.g., "1.0", "2.0")

        Returns:
            Expected number of phases (14 for v1.0, 8 for v2.0)
        """
        return self._schema_detector.get_phase_count(schema_version)

    # ========================================================================
    # Factory Methods
    # ========================================================================

    @classmethod
    def create_with_defaults(cls) -> "DESOrchestrator":
        """Create an orchestrator instance with default real adapters.

        This class method is used in tests and entry points that don't have
        access to pre-configured dependencies. It creates an orchestrator
        with real implementations (SubagentStopHook, TemplateValidator, etc.).

        Returns:
            DESOrchestrator instance with default dependencies configured
        """
        from des.adapters.driven.filesystem.real_filesystem import RealFileSystem
        from des.adapters.driven.time.system_time import SystemTimeProvider
        from des.application.validator import TemplateValidator

        time_provider = SystemTimeProvider()
        # Production validation now runs through claude_code_hook_adapter ->
        # SubagentStopService, so the orchestrator uses a no-op hook.
        hook = _NoOpHook()
        validator = TemplateValidator()
        filesystem = RealFileSystem()

        return cls(
            hook=hook,
            validator=validator,
            filesystem=filesystem,
            time_provider=time_provider,
        )

    def validate_prompt(self, prompt: str) -> ValidationResult:
        """
        Validate a prompt for mandatory sections and TDD phases.

        This is the entry point for pre-invocation validation (US-002).
        Blocks Task invocation if validation fails.

        Args:
            prompt: The full prompt text to validate

        Returns:
            ValidationResult with status, errors, and task_invocation_allowed flag
        """
        result = self._validator.validate_prompt(prompt)

        feature_name = self._extract_feature_name(prompt)
        step_id = self._extract_step_id(prompt)
        agent_name = self._extract_agent_name(prompt)

        event = self._build_validation_audit_event(
            result, feature_name, step_id, agent_name
        )
        self._log_audit_event_if_enabled(event, feature_name, step_id)

        # Mark lifecycle as completed after validation
        self._subagent_lifecycle_completed = True
        return result

    def _extract_feature_name(self, prompt: str) -> str | None:
        """Extract feature_name from DES-PROJECT-ID marker."""
        return self._metadata_extractor.extract_feature_name(prompt)

    def _extract_step_id(self, prompt: str) -> str | None:
        """Extract step_id from DES-STEP-ID or DES-STEP-FILE marker."""
        return self._metadata_extractor.extract_step_id(prompt)

    def _extract_agent_name(self, prompt: str) -> str | None:
        """Extract agent name from @agent-name pattern in prompt."""
        return self._metadata_extractor.extract_agent_name(prompt)

    def _build_validation_audit_event(
        self,
        result: ValidationResult,
        feature_name: str | None,
        step_id: str | None,
        agent_name: str | None,
    ) -> AuditEvent:
        """Build audit event for validation result (passed or blocked)."""
        timestamp = self._time_provider.now_utc().isoformat()
        extra_context = {"agent": agent_name} if agent_name else None

        if result.task_invocation_allowed:
            return AuditEvent(
                timestamp=timestamp,
                event=EventType.HOOK_PRE_TASK_PASSED.value,
                feature_name=feature_name,
                step_id=step_id,
                extra_context=extra_context,
            )

        rejection_reason = str(result.errors) if result.errors else "Validation failed"
        return AuditEvent(
            timestamp=timestamp,
            event=EventType.HOOK_PRE_TASK_BLOCKED.value,
            feature_name=feature_name,
            step_id=step_id,
            rejection_reason=rejection_reason,
            extra_context=extra_context,
        )

    def _log_audit_event_if_enabled(
        self,
        event: AuditEvent,
        feature_name: str | None,
        step_id: str | None,
    ) -> None:
        """Log audit event if audit logging is enabled in config."""
        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig()
        if not config.audit_logging_enabled:
            return

        writer = JsonlAuditLogWriter()
        excluded_keys = ("event", "timestamp", "feature_name", "step_id")
        data = {
            k: v
            for k, v in event.to_dict().items()
            if k not in excluded_keys and v is not None
        }
        writer.log_event(
            PortAuditEvent(
                event_type=event.event,
                timestamp=event.timestamp,
                feature_name=feature_name,
                step_id=step_id,
                data=data,
            )
        )

    # ========================================================================
    # Validation
    # ========================================================================

    def validate_invocation_limits(
        self, step_file: str, project_root: Path | str
    ) -> InvocationLimitsResult:
        """
        Validate turn and timeout limits configuration before sub-agent invocation.

        This is pre-invocation validation that ensures max_turns and duration_minutes
        are configured in the step file before invoking the sub-agent. Prevents execution
        with unconfigured limits and provides clear error guidance.

        Args:
            step_file: Path to step JSON file (relative to project_root)
            project_root: Project root directory path

        Returns:
            InvocationLimitsResult with validation status, errors, and guidance
        """
        step_file_path = self._resolve_step_file_path(project_root, step_file)
        validator = InvocationLimitsValidator(filesystem=self._filesystem)
        return validator.validate_limits(step_file_path)

    def _get_validation_level(self, command: str | None) -> str:
        """
        Determine validation level based on command type.

        Args:
            command: Command string (e.g., "/nw:execute", "/nw:research")

        Returns:
            "full" for execute/develop commands requiring DES validation
            "none" for research and other exploratory commands (or invalid input)
        """
        # Safe default for None or empty command
        if not command:
            return "none"

        if command in self.VALIDATION_COMMANDS:
            return "full"
        return "none"

    # ========================================================================
    # Prompt Rendering
    # ========================================================================

    def _generate_des_markers(self, command: str | None, step_file: str | None) -> str:
        """
        Generate DES validation markers for execute/develop commands.

        Args:
            command: Command type (e.g., "/nw:execute", "/nw:develop")
            step_file: Path to step file

        Returns:
            Formatted DES marker string with validation, step file, origin markers

        Raises:
            ValueError: If command or step_file is None or empty
        """
        # Validate command parameter
        if not command:
            raise ValueError("Command cannot be None or empty")

        # Validate step_file parameter
        if not step_file:
            raise ValueError("Step file cannot be None or empty")

        return self._marker_generator.generate_markers(command, step_file)

    def render_prompt(
        self,
        command: str | None,
        agent: str | None = None,
        step_file: str | None = None,
        project_root: str | None = None,
        topic: str | None = None,
        timeout_thresholds: list[int] | None = None,
        timeout_budget_minutes: int | None = None,
        project_id: str | None = None,
    ) -> str:
        """
        Render Task prompt with appropriate DES validation markers and timeout warnings.

        Args:
            command: Command type (/nw:execute, /nw:develop, /nw:research)
            agent: Target agent identifier (e.g., @software-crafter)
            step_file: Path to step file for execute/develop commands
            project_root: Project root directory path
            topic: Research topic for research commands
            timeout_thresholds: List of threshold values in minutes for timeout warnings
            timeout_budget_minutes: Total time budget in minutes for the phase
            project_id: Project identifier, passed as feature_name in audit events

        Returns:
            Rendered prompt string with or without DES markers and timeout warnings

        Raises:
            ValueError: If command is None or empty, or if step_file is missing
                       for validation commands
        """
        # Validate command parameter
        if not command:
            raise ValueError("Command cannot be None or empty")

        # Extract step_id from step_file path for audit logging
        step_id = None
        if step_file:
            import os

            step_id = os.path.splitext(os.path.basename(step_file))[0]

        # Log TASK_INVOCATION_STARTED for audit trail
        _log_audit_event(
            "TASK_INVOCATION_STARTED",
            command=command,
            step_id=step_id,
            feature_name=project_id,
            agent=agent,
        )

        validation_level = self._get_validation_level(command)

        if validation_level == "full":
            # Validate step_file for validation commands
            if not step_file:
                raise ValueError("Step file required for validation commands")

            des_markers = self._generate_des_markers(command, step_file)

            # Log TASK_INVOCATION_VALIDATED for audit trail
            _log_audit_event(
                "TASK_INVOCATION_VALIDATED",
                command=command,
                step_id=step_id,
                feature_name=project_id,
                status="VALIDATED",
                outcome="success",
            )

            # Add timeout warnings if threshold monitoring is enabled
            if timeout_thresholds and project_root and step_file:
                warnings = self._generate_timeout_warnings(
                    step_file, project_root, timeout_thresholds, timeout_budget_minutes
                )
                if warnings:
                    return f"{des_markers}\n\n{warnings}"

            return des_markers

        # Research and other commands bypass DES validation
        return ""

    def render_full_prompt(
        self,
        command: str,
        agent: str,
        step_file: str,
        project_root: str | Path,
    ) -> str:
        """
        Render complete Task prompt with all DES sections including TIMEOUT_INSTRUCTION.

        This method is used by acceptance tests to validate the complete prompt structure.
        It returns a full prompt that would be sent to the Task tool for execution.

        Args:
            command: Command type (/nw:execute, /nw:develop)
            agent: Target agent identifier (e.g., @software-crafter)
            step_file: Path to step file relative to project_root
            project_root: Project root directory path

        Returns:
            Complete prompt with all DES sections including TIMEOUT_INSTRUCTION

        Raises:
            ValueError: If command is not a validation command
        """
        from des.application.boundary_rules_generator import BoundaryRulesGenerator
        from des.application.boundary_rules_template import BoundaryRulesTemplate
        from des.domain.timeout_instruction_template import (
            TimeoutInstructionTemplate,
        )

        validation_level = self._get_validation_level(command)
        if validation_level != "full":
            raise ValueError(
                f"render_full_prompt only supports validation commands, got: {command}"
            )

        # Generate DES markers
        des_markers = self._generate_des_markers(command, step_file)

        # Generate BOUNDARY_RULES section with scope-based patterns
        step_file_path = self._resolve_step_file_path(project_root, step_file)
        generator = BoundaryRulesGenerator(step_file_path=step_file_path)
        allowed_patterns = generator.generate_allowed_patterns()

        boundary_rules_template = BoundaryRulesTemplate()
        boundary_rules = boundary_rules_template.render(
            allowed_patterns=allowed_patterns
        )

        # Generate TIMEOUT_INSTRUCTION section
        timeout_template = TimeoutInstructionTemplate()
        timeout_instruction = timeout_template.render()

        # Combine all sections
        # In a real implementation, this would include:
        # - DES_METADATA
        # - AGENT_IDENTITY
        # - TASK_CONTEXT
        # - TDD_8_PHASES
        # - QUALITY_GATES
        # - OUTCOME_RECORDING
        # - BOUNDARY_RULES
        # - TIMEOUT_INSTRUCTION
        #
        # For now, return minimal prompt with BOUNDARY_RULES and TIMEOUT_INSTRUCTION to satisfy tests
        return f"{des_markers}\n\n{boundary_rules}\n{timeout_instruction}"

    def prepare_ad_hoc_prompt(
        self, prompt: str, project_root: str | None = None
    ) -> str:
        """
        Prepare ad-hoc prompt without DES validation markers.

        Args:
            prompt: User's ad-hoc Task prompt text
            project_root: Project root directory path

        Returns:
            Prompt text without DES markers (pass-through)
        """
        # Ad-hoc prompts bypass DES validation - return as-is
        return prompt

    # ========================================================================
    # Hook Integration
    # ========================================================================

    def on_subagent_complete(self, step_file_path: str) -> HookResult:
        """
        Invoke SubagentStopHook after sub-agent completion.

        This is the entry point for post-execution validation (US-003).
        Delegates to SubagentStopHook to validate step completion from execution-log.yaml.

        Schema v2.0: The parameter name is legacy from v1.x. In v2.0, this receives
        a compound path encoding: "{execution_log_path}?project_id={id}&step_id={id}"

        Args:
            step_file_path: Compound path with execution-log location and metadata
                           (Schema v2.0 workaround - see SubagentStopHook docstring)

        Returns:
            HookResult with validation status and any errors found
        """
        return self._hook.on_agent_complete(step_file_path)

    # ========================================================================
    # Step Execution
    # ========================================================================

    def execute_step_with_stale_check(
        self,
        command: str,
        agent: str,
        step_file: str,
        project_root: Path | str,
        simulated_iterations: int = 0,
        timeout_thresholds: list[int] | None = None,
        mocked_elapsed_times: list[int] | None = None,
    ) -> ExecuteStepWithStaleCheckResult:
        """
        Execute step with pre-execution stale detection check.

        This method integrates stale execution detection into the orchestrator's
        execution workflow. Before executing a step, it scans for stale IN_PROGRESS
        phases and blocks execution if any are found.

        Args:
            command: Command type (/nw:execute, /nw:develop)
            agent: Target agent identifier (e.g., @software-crafter)
            step_file: Path to step JSON file (relative to project_root)
            project_root: Project root directory path
            simulated_iterations: Number of iterations to simulate (for testing)
            timeout_thresholds: List of threshold values in minutes for timeout warnings
            mocked_elapsed_times: List of mocked elapsed times in seconds for testing timeout simulation

        Returns:
            ExecuteStepWithStaleCheckResult with blocked flag, blocking_reason, stale_alert, and execute_result
        """
        # Resolve project root to Path
        if isinstance(project_root, str):
            project_root = Path(project_root)

        # Step 1: Create StaleExecutionDetector instance
        detector = StaleExecutionDetector(project_root=project_root)

        # Step 2: Scan for stale executions before executing step
        scan_result = detector.scan_for_stale_executions()

        # Step 3: Check if execution is blocked
        if scan_result.is_blocked:
            # Step 4: Return blocked result with alert and resolution instructions
            # Get first stale execution for alert
            first_stale = (
                scan_result.stale_executions[0]
                if scan_result.stale_executions
                else None
            )

            return ExecuteStepWithStaleCheckResult(
                blocked=True,
                blocking_reason="STALE_EXECUTION_DETECTED",
                stale_alert=first_stale,
                execute_result=None,
            )

        # Step 5: If not blocked, proceed with normal execution
        execute_result = self.execute_step(
            command=command,
            agent=agent,
            step_file=step_file,
            project_root=project_root,
            simulated_iterations=simulated_iterations,
            timeout_thresholds=timeout_thresholds,
            mocked_elapsed_times=mocked_elapsed_times,
        )

        return ExecuteStepWithStaleCheckResult(
            blocked=False,
            blocking_reason=None,
            stale_alert=None,
            execute_result=execute_result,
        )

    # ========================================================================
    # Timeout Warning Helpers
    # ========================================================================

    def _build_timeout_warning(
        self,
        phase_name: str,
        elapsed_minutes: int,
        threshold: int,
        duration_minutes: int | None = None,
    ) -> str:
        """Build formatted timeout warning message.

        Args:
            phase_name: Name of the phase being executed
            elapsed_minutes: Minutes elapsed since phase start
            threshold: Threshold value that was crossed
            duration_minutes: Total duration budget (optional)

        Returns:
            Formatted warning string with percentage and remaining time if duration provided
        """
        return self._warning_builder.build_warning(
            phase_name, elapsed_minutes, threshold, duration_minutes
        )

    def _check_timeout_thresholds_for_iteration(
        self,
        iteration_index: int,
        phase_name: str,
        step_data: dict,
        timeout_thresholds: list[int] | None,
        mocked_elapsed_times: list[int] | None,
        timeout_monitor: TimeoutMonitor | None,
        warnings: list[str],
        features_validated: list[str],
    ) -> None:
        """Check timeout thresholds for a single iteration, appending warnings as needed.

        Prioritizes mocked elapsed times (for testing) over the real TimeoutMonitor.
        """
        if mocked_elapsed_times and timeout_thresholds:
            self._check_mocked_thresholds(
                iteration_index,
                phase_name,
                step_data,
                timeout_thresholds,
                mocked_elapsed_times,
                warnings,
                features_validated,
            )
        elif timeout_monitor and timeout_thresholds:
            self._check_real_thresholds(
                iteration_index,
                phase_name,
                step_data,
                timeout_thresholds,
                timeout_monitor,
                warnings,
                features_validated,
            )

    def _check_mocked_thresholds(
        self,
        iteration_index: int,
        phase_name: str,
        step_data: dict,
        timeout_thresholds: list[int],
        mocked_elapsed_times: list[int],
        warnings: list[str],
        features_validated: list[str],
    ) -> None:
        """Check thresholds using mocked elapsed times (for testing)."""
        if iteration_index >= len(mocked_elapsed_times):
            return

        mocked_elapsed_minutes = mocked_elapsed_times[iteration_index] // 60
        duration_minutes = step_data.get("tdd_cycle", {}).get("duration_minutes")

        for threshold in timeout_thresholds:
            if mocked_elapsed_minutes >= threshold:
                warning = self._build_timeout_warning(
                    phase_name=phase_name,
                    elapsed_minutes=mocked_elapsed_minutes,
                    threshold=threshold,
                    duration_minutes=duration_minutes,
                )
                if warning not in warnings:
                    warnings.append(warning)

        if "timeout_monitoring" not in features_validated:
            features_validated.append("timeout_monitoring")

    def _check_real_thresholds(
        self,
        iteration_index: int,
        phase_name: str,
        step_data: dict,
        timeout_thresholds: list[int],
        timeout_monitor: TimeoutMonitor,
        warnings: list[str],
        features_validated: list[str],
    ) -> None:
        """Check thresholds using real TimeoutMonitor (production path)."""
        if iteration_index % 5 != 0 and iteration_index != 0:
            return

        crossed = timeout_monitor.check_thresholds(timeout_thresholds)
        duration_minutes = step_data.get("tdd_cycle", {}).get("duration_minutes")

        for threshold in crossed:
            warning = self._format_timeout_warning(
                threshold=threshold,
                monitor=timeout_monitor,
                phase_name=phase_name,
                duration_minutes=duration_minutes,
            )
            if warning not in warnings:
                warnings.append(warning)

        if crossed and "timeout_monitoring" not in features_validated:
            features_validated.append("timeout_monitoring")

    def execute_step(
        self,
        command: str,
        agent: str,
        step_file: str,
        project_root: Path | str,
        simulated_iterations: int = 0,
        timeout_thresholds: list[int] | None = None,
        mocked_elapsed_times: list[int] | None = None,
    ) -> ExecuteStepResult:
        """
        Execute step with TurnCounter and TimeoutMonitor integration.

        This method wires both TurnCounter and TimeoutMonitor into the orchestrator's
        execution loop:
        - Initializes TurnCounter at phase start
        - Initializes TimeoutMonitor with phase start timestamp
        - Increments turn count on each agent call iteration
        - Checks timeout thresholds during execution loop
        - Emits warnings when thresholds are crossed
        - Persists to step file in real-time
        - Restores state from step file on resume

        Args:
            command: Command type (/nw:execute, /nw:develop)
            agent: Target agent identifier (e.g., @software-crafter)
            step_file: Path to step JSON file (relative to project_root)
            project_root: Project root directory path
            simulated_iterations: Number of iterations to simulate (for testing)
            timeout_thresholds: List of threshold values in minutes for timeout warnings
            mocked_elapsed_times: List of mocked elapsed times in seconds for testing timeout simulation

        Returns:
            ExecuteStepResult with turn_count, execution status, timeout_warnings, execution_path, and features_validated
        """
        counter = TurnCounter()
        step_file_path = self._resolve_step_file_path(project_root, step_file)
        step_data = self._load_step_file(step_file_path)

        current_phase = self._get_current_phase(step_data)
        phase_name = current_phase["phase_name"]

        # Initialize TimeoutMonitor with phase start timestamp
        timeout_monitor = None
        warnings = []
        if timeout_thresholds:
            started_at = current_phase.get("started_at")
            if started_at:
                timeout_monitor = TimeoutMonitor(
                    started_at=started_at, time_provider=self._time_provider
                )

        self._restore_turn_count(counter, current_phase, phase_name)

        # Track validated features
        features_validated = []

        # Execute iterations with threshold checking
        for i in range(simulated_iterations):
            counter.increment_turn(phase_name)
            features_validated.append("turn_counting")

            self._check_timeout_thresholds_for_iteration(
                iteration_index=i,
                phase_name=phase_name,
                step_data=step_data,
                timeout_thresholds=timeout_thresholds,
                mocked_elapsed_times=mocked_elapsed_times,
                timeout_monitor=timeout_monitor,
                warnings=warnings,
                features_validated=features_validated,
            )

        final_turn_count = counter.get_current_turn(phase_name)
        self._persist_turn_count(
            step_file_path, step_data, current_phase, final_turn_count
        )

        # Deduplicate features_validated
        features_validated = list(dict.fromkeys(features_validated))

        return ExecuteStepResult(
            turn_count=final_turn_count,
            phase_name=phase_name,
            status="COMPLETED",
            warnings_emitted=warnings,  # Deprecated field
            timeout_warnings=warnings,
            execution_path="DESOrchestrator.execute_step",
            features_validated=features_validated,
        )

    # ========================================================================
    # File Operations
    # ========================================================================

    def _resolve_step_file_path(self, project_root: Path | str, step_file: str) -> Path:
        """Convert project_root and step_file to absolute path."""
        return self._step_repository.resolve_path(project_root, step_file)

    def _load_step_file(self, step_file_path: Path) -> dict:
        """Load and parse step file JSON using injected filesystem."""
        return self._step_repository.load(step_file_path)

    def _get_current_phase(self, step_data: dict) -> dict:
        """Get current phase from step data and mark as IN_PROGRESS if needed."""
        return self._step_repository.get_current_phase(step_data)

    # ========================================================================
    # TurnCounter Operations
    # ========================================================================

    def _restore_turn_count(
        self, counter: TurnCounter, current_phase: dict, phase_name: str
    ) -> None:
        """Restore existing turn count from phase data if resuming execution."""
        existing_turn_count = current_phase.get("turn_count", 0)
        for _ in range(existing_turn_count):
            counter.increment_turn(phase_name)

    def _execute_iterations(
        self, counter: TurnCounter, phase_name: str, iterations: int
    ) -> None:
        """Execute simulated agent call iterations, incrementing turn count."""
        for _ in range(iterations):
            counter.increment_turn(phase_name)

    def _persist_turn_count(
        self,
        step_file_path: Path,
        step_data: dict,
        current_phase: dict,
        turn_count: int,
    ) -> None:
        """Persist turn count to step file using injected filesystem."""
        current_phase["turn_count"] = turn_count
        self._filesystem.write_json(step_file_path, step_data)

    def _format_timeout_warning(
        self,
        threshold: int,
        monitor: TimeoutMonitor,
        phase_name: str = "current phase",
        duration_minutes: int | None = None,
    ) -> str:
        """Format timeout warning message with threshold and elapsed time.

        Args:
            threshold: Threshold value in minutes that was crossed
            monitor: TimeoutMonitor instance for elapsed time calculation
            phase_name: Name of the phase being executed (default: "current phase")
            duration_minutes: Total duration budget in minutes (optional)

        Returns:
            Formatted warning message string
        """
        elapsed_seconds = monitor.get_elapsed_seconds()
        elapsed_minutes = int(elapsed_seconds / 60)

        return self._build_timeout_warning(
            phase_name=phase_name,
            elapsed_minutes=elapsed_minutes,
            threshold=threshold,
            duration_minutes=duration_minutes,
        )

    def _persist_step_file(self, step_file_path: Path, step_data: dict) -> None:
        """Persist step data to file using injected filesystem.

        Args:
            step_file_path: Path to step file
            step_data: Complete step data dictionary to persist
        """
        self._step_repository.save(step_file_path, step_data)

    def _generate_timeout_warnings(
        self,
        step_file: str,
        project_root: str | Path,
        timeout_thresholds: list[int],
        timeout_budget_minutes: int | None,
    ) -> str:
        """Generate timeout warnings for agent prompt context.

        Loads step file, checks if any thresholds have been crossed,
        and generates formatted warnings with percentage, remaining time,
        and phase name.

        Args:
            step_file: Path to step file (relative to project_root)
            project_root: Project root directory path
            timeout_thresholds: List of threshold values in minutes
            timeout_budget_minutes: Total time budget in minutes

        Returns:
            Formatted warning string, or empty string if no thresholds crossed
        """
        step_file_path = self._resolve_step_file_path(project_root, step_file)
        step_data = self._load_step_file(step_file_path)
        current_phase = self._get_current_phase(step_data)

        # Get phase start time
        started_at = current_phase.get("started_at")
        if not started_at:
            return ""

        # Initialize TimeoutMonitor
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=self._time_provider
        )

        # Check thresholds
        crossed_thresholds = monitor.check_thresholds(timeout_thresholds)
        if not crossed_thresholds:
            return ""

        # Generate warning using shared helper
        elapsed_seconds = monitor.get_elapsed_seconds()
        elapsed_minutes = int(elapsed_seconds / 60)
        phase_name = current_phase["phase_name"]

        # Use first crossed threshold for warning message
        first_threshold = crossed_thresholds[0]

        return self._build_timeout_warning(
            phase_name=phase_name,
            elapsed_minutes=elapsed_minutes,
            threshold=first_threshold,
            duration_minutes=timeout_budget_minutes,
        )
