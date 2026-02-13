"""Deliver Integrity Verifier - cross-references roadmap steps against execution-log.

Pure domain service that verifies all roadmap steps have valid DES execution-log
entries with all required TDD phases. Detects steps implemented without DES
monitoring (no entries) and steps with incomplete TDD cycles (partial entries).

This is called by the deliver orchestrator before finalize to ensure all steps
went through proper DES-monitored execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StepIntegrity:
    """Integrity status for a single roadmap step.

    Attributes:
        step_id: The step identifier
        has_execution_log: True if any execution-log entries exist for this step
        phase_count: Number of phases found (out of expected total)
        missing_phases: List of phase names not found in execution-log
    """

    step_id: str
    has_execution_log: bool
    phase_count: int
    missing_phases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DeliverIntegrityResult:
    """Result of deliver integrity verification.

    Attributes:
        is_valid: True if all steps have complete DES traces
        steps_verified: Total number of roadmap steps checked
        violations: Steps with missing or incomplete execution-log entries
        reason: Human-readable summary of violations
    """

    is_valid: bool
    steps_verified: int
    violations: list[StepIntegrity] = field(default_factory=list)
    reason: str | None = None


class DeliverIntegrityVerifier:
    """Verifies all roadmap steps have valid DES execution-log entries."""

    def __init__(self, required_phases: list[str]) -> None:
        """Initialize with required TDD phases.

        Args:
            required_phases: Inject from TDDSchema.tdd_phases to avoid drift.
        """
        self._required_phases = required_phases

    def verify(
        self,
        roadmap_steps: list[str],
        execution_log_entries: dict[str, list[str]],
    ) -> DeliverIntegrityResult:
        """Verify all roadmap steps have valid DES execution-log entries.

        Args:
            roadmap_steps: List of step IDs from roadmap.yaml
            execution_log_entries: Dict mapping step_id -> list of phase names found
        """
        violations = []
        for step_id in roadmap_steps:
            phases = execution_log_entries.get(step_id, [])
            missing = [p for p in self._required_phases if p not in phases]
            if missing:
                violations.append(
                    StepIntegrity(
                        step_id=step_id,
                        has_execution_log=bool(phases),
                        phase_count=len(phases),
                        missing_phases=missing,
                    )
                )

        if violations:
            no_entry = [v for v in violations if not v.has_execution_log]
            partial = [v for v in violations if v.has_execution_log]
            reason_parts = []
            if no_entry:
                reason_parts.append(
                    f"{len(no_entry)} step(s) have NO execution-log entries "
                    f"(likely implemented without DES): {[v.step_id for v in no_entry]}"
                )
            if partial:
                expected = len(self._required_phases)
                reason_parts.append(
                    f"{len(partial)} step(s) have incomplete TDD phases: "
                    f"{[f'{v.step_id} ({v.phase_count}/{expected})' for v in partial]}"
                )
            return DeliverIntegrityResult(
                is_valid=False,
                steps_verified=len(roadmap_steps),
                violations=violations,
                reason="; ".join(reason_parts),
            )

        return DeliverIntegrityResult(
            is_valid=True,
            steps_verified=len(roadmap_steps),
            violations=[],
        )
