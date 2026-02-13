"""
Pre-Invocation Template Validator

Validates that DES prompts contain all mandatory sections and TDD phases
before Task invocation, preventing incomplete instructions from reaching sub-agents.

Uses canonical 5-phase TDD cycle from step-tdd-cycle-schema.json v4.0 (single source of truth).
All phase names, skip prefixes, and validation rules loaded from schema.

MANDATORY SECTIONS (9):
1. DES_METADATA
2. AGENT_IDENTITY
3. TASK_CONTEXT
4. TDD_PHASES (from schema)
5. QUALITY_GATES
6. OUTCOME_RECORDING
7. RECORDING_INTEGRITY
8. BOUNDARY_RULES
9. TIMEOUT_INSTRUCTION

MANDATORY TDD PHASES (5 from schema):
1. PREPARE, 2. RED_ACCEPTANCE, 3. RED_UNIT, 4. GREEN (merged GREEN_UNIT + GREEN_ACCEPTANCE)
5. COMMIT (absorbs FINAL_VALIDATE)
Note: REVIEW moved to deliver-level Phase 4 (Adversarial Review via /nw:review)
Note: REFACTOR moved to deliver-level Phase 3 (Complete Refactoring L1-L4 via /nw:refactor)
"""

import re
import time
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of template validation."""

    status: str  # "PASSED" or "FAILED"
    errors: list[str]
    task_invocation_allowed: bool
    duration_ms: float
    recovery_guidance: list[str] = (
        None  # Actionable guidance for fixing validation errors
    )


class MandatorySectionChecker:
    """
    Validates that all 9 mandatory sections are present in prompt.

    Mandatory sections ensure prompts contain complete instructions for sub-agents,
    preventing "I didn't know about X" excuses during execution.
    """

    MANDATORY_SECTIONS = [
        "DES_METADATA",  # Step metadata and command
        "AGENT_IDENTITY",  # Which agent executes this step
        "TASK_CONTEXT",  # What needs to be implemented
        "TDD_PHASES",  # All TDD phases to execute (schema v4.0 canonical)
        "QUALITY_GATES",  # Quality validation criteria
        "OUTCOME_RECORDING",  # How to track progress
        "RECORDING_INTEGRITY",  # Skip prefixes + anti-fraud rules
        "BOUNDARY_RULES",  # Scope and file modifications allowed
        "TIMEOUT_INSTRUCTION",  # Turn budget and exit conditions
    ]

    # Recovery guidance for each mandatory section
    RECOVERY_GUIDANCE_MAP = {
        "DES_METADATA": "Add DES_METADATA section with step file path and command name",
        "AGENT_IDENTITY": "Add AGENT_IDENTITY section specifying which agent executes this step",
        "TASK_CONTEXT": "Add TASK_CONTEXT section describing what needs to be implemented",
        "TDD_PHASES": "Add TDD_PHASES section listing all 5 phases: PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT",
        "QUALITY_GATES": "Add QUALITY_GATES section defining validation criteria (G1-G6)",
        "OUTCOME_RECORDING": "Add OUTCOME_RECORDING section describing how to track phase completion",
        "RECORDING_INTEGRITY": (
            "Add RECORDING_INTEGRITY section with valid skip prefixes "
            "(NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING) "
            "and anti-fraud rules. See ~/.claude/commands/nw/execute.md"
        ),
        "BOUNDARY_RULES": "Add BOUNDARY_RULES section specifying which files can be modified",
        "TIMEOUT_INSTRUCTION": "Add TIMEOUT_INSTRUCTION section with turn budget guidance",
    }

    def validate(self, prompt: str) -> list[str]:
        """
        Validate that all mandatory sections are present in prompt.

        Args:
            prompt: The full prompt text to validate

        Returns:
            List of error messages (empty if all sections present)
        """
        errors = []

        for section in self.MANDATORY_SECTIONS:
            section_marker = f"# {section}"
            if section_marker not in prompt:
                errors.append(f"MISSING: Mandatory section '{section}' not found")

        return errors

    def get_recovery_guidance(self, errors: list[str]) -> list[str]:
        """
        Generate actionable recovery guidance for validation errors.

        Args:
            errors: List of error messages from validation

        Returns:
            List of recovery guidance strings for all missing sections,
            each prefixed with "FIX: " to integrate inline with error messages.
        """
        if not errors:
            return None

        guidance_items = []
        for error in errors:
            if "MISSING: Mandatory section" in error:
                # Extract section name from error message
                for section in self.MANDATORY_SECTIONS:
                    if section in error:
                        guidance = self.RECOVERY_GUIDANCE_MAP.get(section)
                        if guidance:
                            # Append FIX: prefix for inline error message integration (AC-005.4)
                            guidance_items.append(f"FIX: {guidance}")
                        break

        if guidance_items:
            return guidance_items
        return None


class TDDPhaseValidator:
    """
    Validates that required TDD phases are mentioned in prompt.

    Uses canonical 5-phase TDD cycle from step-tdd-cycle-schema.json v4.0:
    PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT

    Note: REVIEW moved to deliver-level Phase 4 (Adversarial Review)
    Note: REFACTOR moved to deliver-level Phase 3 (Complete Refactoring L1-L4)
    """

    def __init__(self):
        """Initialize validator with schema loader."""
        from des.domain.tdd_schema import get_tdd_schema

        self._schema = get_tdd_schema()
        self.MANDATORY_PHASES = self._schema.tdd_phases

    def validate(self, prompt: str) -> list[str]:
        """
        Validate that all required TDD phases are mentioned in prompt.

        Uses canonical 5-phase TDD cycle from schema (single source of truth).

        Detects phases by looking for patterns:
        - Numbered list items (e.g., "1. PREPARE")
        - Phase names in text (e.g., "PREPARE")
        - Shorthand references like "All 5 phases listed"

        But excludes comments mentioning missing phases (e.g., "# MISSING: REFACTOR_L3")

        Args:
            prompt: The full prompt text to validate

        Returns:
            List of error messages (empty if all phases present)
        """
        # Check for shorthand pattern (count-agnostic)
        shorthand_pattern = (
            r"(?i)all\s+\d+\s+phases?\s+(listed|mentioned|included|present)"
        )
        if re.search(shorthand_pattern, prompt):
            return []  # Accept shorthand as valid

        errors = []

        for phase in self.MANDATORY_PHASES:
            if not self._is_phase_present_in_prompt(phase, prompt):
                errors.append(f"INCOMPLETE: TDD phase '{phase}' not mentioned")

        return errors

    def _is_phase_present_in_prompt(self, phase: str, prompt: str) -> bool:
        """Check if a phase is mentioned in a non-missing context within the prompt."""
        lines_containing_phase = [
            line.strip() for line in prompt.split("\n") if phase in line
        ]

        for line in lines_containing_phase:
            if self._is_missing_context(phase, line):
                continue
            if phase in line:
                return True

        return False

    @staticmethod
    def _is_missing_context(phase: str, line: str) -> bool:
        """Check if a line only mentions the phase in a 'missing' context."""
        return bool(
            re.search(rf"\(.*\b{phase}\b.*\)", line)  # (missing COMMIT) format
            or re.search(
                rf"\b(without|missing|no)\s+{phase}\b", line, re.IGNORECASE
            )  # descriptive text
            or re.search(rf"# MISSING:\s*{phase}", line)  # comment format
        )


class DESMarkerValidator:
    """
    Validates the DES-VALIDATION marker format in prompts.

    Ensures prompts contain a valid HTML comment marker:
    <!-- DES-VALIDATION: required -->

    The marker value MUST be exactly 'required' (case-sensitive).
    """

    def validate(self, prompt: str) -> list:
        """
        Validate DES-VALIDATION marker in prompt.

        Args:
            prompt: The full prompt text to validate

        Returns:
            List of error messages (empty if marker is valid)
        """
        errors = []

        # Pattern for DES-VALIDATION marker: <!-- DES-VALIDATION: value -->
        pattern = r"<!--\s*DES-VALIDATION\s*:\s*(\w+)\s*-->"
        match = re.search(pattern, prompt)

        if not match:
            # Marker not found
            errors.append("INVALID_MARKER: DES-VALIDATION marker not found")
            return errors

        # Extract value and normalize whitespace
        value = match.group(1).strip()

        # Value MUST be exactly 'required' (case-sensitive)
        if value != "required":
            errors.append(
                f"INVALID_MARKER: DES-VALIDATION value must be 'required', got '{value}'"
            )

        return errors


class ExecutionLogValidator:
    """
    Validates phase execution log for state violations and schema compliance.

    Uses canonical TDD cycle from step-tdd-cycle-schema.json v4.0.
    Detects abandoned phases, missing required fields, and invalid state sequences
    to ensure phase execution logs are complete and consistent.
    """

    def __init__(self):
        """Initialize validator with schema loader."""
        from des.domain.tdd_schema import get_tdd_schema

        self._schema = get_tdd_schema()

    def validate(
        self,
        phase_log: list[dict],
        schema_version: str = "3.0",
        skip_schema_validation: bool = False,
    ) -> list[str]:
        """
        Validate phase execution log for state violations and schema compliance.

        Checks:
        1. Correct number of phases (from schema)
           - SKIPPED if phase_log is empty (no execution log found in prompt)
           - SKIPPED if skip_schema_validation is True
        2. Required phases present (from schema)
           - SKIPPED if phase_log is empty
           - SKIPPED if skip_schema_validation is True
        3. No IN_PROGRESS phases (abandoned state)
        4. EXECUTED phases must have outcome field (PASS/FAIL)
        5. SKIPPED phases must have blocked_by reason
        6. No NOT_EXECUTED phases in log

        Args:
            phase_log: List of phase execution records
            schema_version: Schema version (kept for backward compatibility)
            skip_schema_validation: If True, skip phase count/presence validation.
                Useful for unit tests that only test individual phase state rules.

        Returns:
            List of error messages (empty if all valid)
        """
        errors = []

        # Skip phase count and presence validation if phase_log is empty
        # This happens when no EXECUTION_LOG_* sections are found in the prompt
        # (prompts don't always include execution logs, especially before execution starts)
        if not phase_log:
            return errors

        # Skip schema-level validation if requested (for unit testing individual rules)
        if not skip_schema_validation:
            # Get expected phases and count from schema (single source of truth)
            expected_phases = len(self._schema.tdd_phases)
            required_phases = set(self._schema.tdd_phases)

            # Check phase count
            if len(phase_log) != expected_phases:
                errors.append(
                    f"INVALID: Phase log has {len(phase_log)} phases, "
                    f"expected {expected_phases} phases from schema"
                )

            # Check for required phases
            present_phases = {
                phase.get("phase_name")
                for phase in phase_log
                if phase.get("phase_name")
            }
            missing_phases = required_phases - present_phases
            if missing_phases:
                errors.append(
                    f"INCOMPLETE: Missing required phases: {', '.join(sorted(missing_phases))}"
                )

        for phase in phase_log:
            phase_name = phase.get("phase_name", "unknown")
            status = phase.get("status")

            # Check 1: Detect IN_PROGRESS (abandoned state)
            if status == "IN_PROGRESS":
                errors.append(
                    f"INCOMPLETE: Phase {phase_name} left in IN_PROGRESS state - "
                    f"task may have been abandoned"
                )

            # Check 2: EXECUTED must have outcome
            elif status == "EXECUTED":
                if "outcome" not in phase or phase.get("outcome") is None:
                    errors.append(
                        f"ERROR: Phase {phase_name} EXECUTED but missing outcome field. "
                        f"Must specify outcome (PASS or FAIL)"
                    )

            # Check 3: SKIPPED must have blocked_by
            elif status == "SKIPPED":
                if "blocked_by" not in phase or not phase.get("blocked_by"):
                    errors.append(
                        f"ERROR: Phase {phase_name} SKIPPED but missing blocked_by reason. "
                        f"Must explain why phase was skipped"
                    )

            # Check 4: Reject NOT_EXECUTED
            elif status == "NOT_EXECUTED":
                errors.append(
                    f"ERROR: Phase {phase_name} NOT_EXECUTED. "
                    f"Cannot mark task complete with unexecuted phases"
                )

        return errors

    def get_recovery_guidance(self, errors: list[str]) -> list[str]:
        """
        Generate actionable recovery guidance for validation errors.

        Args:
            errors: List of error messages from validate()

        Returns:
            List of recovery steps for fixing errors, each prefixed with "FIX: "
            for inline integration with error messages (AC-005.4)
        """
        if not errors:
            return None

        guidance_items = []
        for error in errors:
            guidance = self._guidance_for_error(error)
            if guidance:
                guidance_items.append(guidance)

        return guidance_items if guidance_items else None

    @staticmethod
    def _extract_phase_name_from_error(error: str) -> str | None:
        """Extract phase name from error message like 'Phase REVIEW ...'."""
        if "Phase" not in error:
            return None
        parts = error.split("Phase ")
        if len(parts) > 1:
            return parts[1].split(" ")[0]
        return None

    def _guidance_for_error(self, error: str) -> str | None:
        """Generate a single guidance item for an error message."""
        if "IN_PROGRESS" in error:
            phase_name = self._extract_phase_name_from_error(error)
            if phase_name:
                return f"FIX: Complete or rollback the IN_PROGRESS phase {phase_name}"

        elif "SKIPPED" in error and "blocked_by" in error.lower():
            phase_name = self._extract_phase_name_from_error(error)
            if phase_name:
                return f"FIX: Add blocked_by reason explaining why phase {phase_name} was skipped"

        elif "EXECUTED" in error and "outcome" in error.lower():
            phase_name = self._extract_phase_name_from_error(error)
            if phase_name:
                return f"FIX: Add outcome field (PASS/FAIL) to phase {phase_name}"

        elif "NOT_EXECUTED" in error:
            return (
                "FIX: Cannot complete task with NOT_EXECUTED phases. "
                "All required phases must be EXECUTED or explicitly SKIPPED with reason"
            )

        return None


class TemplateValidator:
    """
    Main entry point for template validation.

    Validates that prompts contain all mandatory sections and TDD phases
    before allowing Task invocation.
    """

    def __init__(self):
        """Initialize validator with checkers."""
        self.marker_validator = DESMarkerValidator()
        self.section_checker = MandatorySectionChecker()
        self.phase_validator = TDDPhaseValidator()
        self.execution_log_validator = ExecutionLogValidator()

    def validate_prompt(self, prompt: str) -> ValidationResult:
        """
        Validate a complete prompt for mandatory sections and phases.

        Uses canonical TDD cycle from step-tdd-cycle-schema.json v4.0.

        Args:
            prompt: The full prompt text to validate

        Returns:
            ValidationResult with status, errors, and task invocation permission
        """
        start_time = time.perf_counter()

        # Check marker (first - foundational validation)
        marker_errors = self.marker_validator.validate(prompt)

        # Check sections
        section_errors = self.section_checker.validate(prompt)

        # Check phases (uses canonical 7-phase schema)
        phase_errors = self.phase_validator.validate(prompt)

        # Extract and parse phase_execution_log from prompt
        execution_log_data = self._extract_execution_log_from_prompt(prompt)
        # Validate with schema (always v4.0)
        execution_log_errors = self.execution_log_validator.validate(
            execution_log_data, schema_version="4.0"
        )

        # Combine all errors (marker first, then sections, then phases, then execution log)
        all_errors = (
            marker_errors + section_errors + phase_errors + execution_log_errors
        )

        # Generate recovery guidance for errors
        recovery_guidance = []
        if section_errors:
            section_guidance = self.section_checker.get_recovery_guidance(
                section_errors
            )
            if section_guidance:
                recovery_guidance.extend(section_guidance)
        if execution_log_errors:
            log_guidance = self.execution_log_validator.get_recovery_guidance(
                execution_log_errors
            )
            if log_guidance:
                recovery_guidance.extend(log_guidance)

        # Return None if no guidance was generated
        if not recovery_guidance:
            recovery_guidance = None

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine if invocation is allowed
        status = "PASSED" if not all_errors else "FAILED"
        task_invocation_allowed = not all_errors

        return ValidationResult(
            status=status,
            errors=all_errors,
            task_invocation_allowed=task_invocation_allowed,
            duration_ms=duration_ms,
            recovery_guidance=recovery_guidance,
        )

    def _extract_execution_log_from_prompt(self, prompt: str) -> list[dict]:
        """
        Extract and parse phase execution log from prompt text.

        Searches for section markers (# EXECUTION_LOG_*) and parses multiple
        text format variations into structured phase execution data.

        Supports three distinct format variations:

        Format A (Narrative):
            "Phase REFACTOR_L2 status: IN_PROGRESS (context)"
            → {"phase_name": "REFACTOR_L2", "status": "IN_PROGRESS"}

        Format B (List):
            "EXECUTED: PREPARE, RED_ACCEPTANCE, ...
             NOT_EXECUTED: GREEN_ACCEPTANCE, ..."
            → Multiple dicts, one per phase with respective status

        Format C (Key-Value):
            "Phase RED_UNIT: status=EXECUTED, outcome=null, blocked_by=reason"
            → {"phase_name": "RED_UNIT", "status": "EXECUTED", "outcome": None, "blocked_by": "reason"}

        Args:
            prompt: The full prompt text containing execution log sections

        Returns:
            List[dict] where each dict has:
            - phase_name: str (required)
            - status: str (required, one of: EXECUTED, SKIPPED, IN_PROGRESS, NOT_EXECUTED)
            - outcome: Optional[str] (for EXECUTED phases: PASS or FAIL)
            - blocked_by: Optional[str] (for SKIPPED phases: reason text)

            Returns empty list if no execution log sections found
        """
        phase_log = []
        section_markers = [
            "# EXECUTION_LOG_STATUS",
            "# EXECUTION_LOG_ISSUE",
            "# EXECUTION_LOG_PROBLEM",
            "# EXECUTION_LOG_ERRORS",
            "# EXECUTION_LOG_WITH_SKIP",
            "# EXECUTION_LOG_COMPLETE",
        ]

        for marker in section_markers:
            if marker not in prompt:
                continue

            section_content = self._extract_section_content(prompt, marker)
            if not section_content:
                continue

            phase_log.extend(self._parse_narrative_format(section_content))
            phase_log.extend(self._parse_list_format(section_content))
            phase_log.extend(self._parse_key_value_format(section_content))

        return self._deduplicate_phase_log(phase_log)

    @staticmethod
    def _extract_section_content(prompt: str, marker: str) -> str:
        """Extract text content between a section marker and the next section."""
        marker_index = prompt.find(marker)
        if marker_index == -1:
            return ""

        section_start = marker_index + len(marker)
        next_marker_index = prompt.find("\n#", section_start)
        if next_marker_index == -1:
            return prompt[section_start:]
        return prompt[section_start:next_marker_index]

    @staticmethod
    def _parse_narrative_format(section_content: str) -> list[dict]:
        """Parse Format A: 'Phase PHASE_NAME status: STATUS (optional context)'."""
        entries = []
        matches = re.findall(r"Phase\s+(\w+)\s+status:\s+(\w+)", section_content)
        for phase_name, status in matches:
            entries.append({"phase_name": phase_name, "status": status})
        return entries

    @staticmethod
    def _parse_list_format(section_content: str) -> list[dict]:
        """Parse Format B: 'STATUS: PHASE1, PHASE2, ...'."""
        entries = []
        statuses = ["EXECUTED", "SKIPPED", "IN_PROGRESS", "NOT_EXECUTED"]
        for status in statuses:
            pattern = (
                status
                + r":\s+([A-Z0-9_,\s\-]+?)(?=\n|$|EXECUTED|SKIPPED|IN_PROGRESS|NOT_EXECUTED)"
            )
            matches = re.findall(pattern, section_content)
            for match in matches:
                phase_names = [p.strip() for p in match.split(",") if p.strip()]
                for phase_name in phase_names:
                    if phase_name and re.match(r"^[A-Z0-9_\-]+$", phase_name):
                        entries.append({"phase_name": phase_name, "status": status})
        return entries

    @staticmethod
    def _parse_key_value_format(section_content: str) -> list[dict]:
        """Parse Format C: 'Phase PHASE_NAME: status=STATUS, outcome=VALUE, blocked_by=REASON'."""
        entries = []
        pattern = r"Phase\s+(\w+):\s+status=(\w+)(?:,\s+outcome=(\w+))?(?:,\s+blocked_by=([^\n,]+))?"
        matches = re.findall(pattern, section_content)
        for phase_name, status, outcome, blocked_by in matches:
            entry = {"phase_name": phase_name, "status": status}

            if outcome and outcome.lower() != "null":
                entry["outcome"] = outcome

            if blocked_by:
                blocked_by = blocked_by.strip()
                if not blocked_by.lower().startswith("null"):
                    entry["blocked_by"] = blocked_by

            entries.append(entry)
        return entries

    @staticmethod
    def _deduplicate_phase_log(phase_log: list[dict]) -> list[dict]:
        """Remove duplicate entries by (phase_name, status) key, preserving order."""
        seen = set()
        unique_entries = []
        for entry in phase_log:
            key = (entry.get("phase_name"), entry.get("status"))
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
        return unique_entries
