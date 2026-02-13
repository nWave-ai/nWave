"""Unit tests for domain classes extracted in step 03-01.

Tests for:
- PhaseEvent + PhaseEventParser (phase_event.py)
- MaxTurnsPolicy + PolicyResult (max_turns_policy.py)
- DesMarkerParser + DesMarkers (des_marker_parser.py)
- StepCompletionValidator + CompletionResult (step_completion_validator.py)

All domain classes are pure (no I/O), so tests are fast and deterministic.
"""

import pytest

from des.domain.des_marker_parser import DesMarkerParser, DesMarkers
from des.domain.max_turns_policy import MaxTurnsPolicy, PolicyResult
from des.domain.phase_event import PhaseEvent, PhaseEventParser
from des.domain.step_completion_validator import (
    CompletionResult,
    StepCompletionValidator,
)
from des.domain.tdd_schema import TDDSchema


# ---------------------------------------------------------------------------
# Helpers: reusable TDDSchema fixture for StepCompletionValidator tests
# ---------------------------------------------------------------------------


def _make_schema() -> TDDSchema:
    """Create a TDDSchema matching production values for testing."""
    return TDDSchema(
        tdd_phases=(
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "COMMIT",
        ),
        valid_statuses=("NOT_EXECUTED", "IN_PROGRESS", "EXECUTED", "SKIPPED"),
        valid_skip_prefixes=(
            "BLOCKED_BY_DEPENDENCY:",
            "NOT_APPLICABLE:",
            "APPROVED_SKIP:",
            "CHECKPOINT_PENDING:",
        ),
        blocking_skip_prefixes=("DEFERRED:",),
        terminal_phases=("COMMIT",),
    )


def _make_event(
    phase: str,
    status: str = "EXECUTED",
    outcome: str = "PASS",
    step_id: str = "01-01",
    timestamp: str = "2026-02-02T10:00:00Z",
) -> PhaseEvent:
    """Create a PhaseEvent with sensible defaults."""
    return PhaseEvent(
        step_id=step_id,
        phase_name=phase,
        status=status,
        outcome=outcome,
        timestamp=timestamp,
    )


def _make_all_passing_events(step_id: str = "01-01") -> list[PhaseEvent]:
    """Create a list of all 5 phases EXECUTED with PASS."""
    phases = [
        "PREPARE",
        "RED_ACCEPTANCE",
        "RED_UNIT",
        "GREEN",
        "COMMIT",
    ]
    return [_make_event(p, step_id=step_id) for p in phases]


# ===========================================================================
# PhaseEvent + PhaseEventParser tests
# ===========================================================================


class TestPhaseEventParser:
    """Tests for PhaseEventParser.parse() and parse_many()."""

    def test_parse_valid_event_string(self):
        parser = PhaseEventParser()
        result = parser.parse("01-01|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z")

        assert result is not None
        assert result.step_id == "01-01"
        assert result.phase_name == "PREPARE"
        assert result.status == "EXECUTED"
        assert result.outcome == "PASS"
        assert result.timestamp == "2026-02-02T10:00:00Z"

    def test_parse_returns_none_for_too_few_fields(self):
        parser = PhaseEventParser()
        assert parser.parse("01-01|PREPARE|EXECUTED") is None
        assert parser.parse("01-01|PREPARE") is None
        assert parser.parse("single") is None
        assert parser.parse("") is None

    def test_parse_handles_extra_fields_gracefully(self):
        parser = PhaseEventParser()
        result = parser.parse(
            "01-01|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z|extra|data"
        )

        assert result is not None
        assert result.step_id == "01-01"
        assert result.phase_name == "PREPARE"

    def test_parse_many_filters_by_step_id(self):
        parser = PhaseEventParser()
        events_raw = [
            "01-01|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z",
            "01-02|PREPARE|EXECUTED|PASS|2026-02-02T10:01:00Z",
            "01-01|RED_ACCEPTANCE|EXECUTED|PASS|2026-02-02T10:05:00Z",
        ]
        result = parser.parse_many(events_raw, step_id="01-01")

        assert len(result) == 2
        assert result[0].phase_name == "PREPARE"
        assert result[1].phase_name == "RED_ACCEPTANCE"

    def test_parse_many_returns_empty_for_no_matches(self):
        parser = PhaseEventParser()
        events_raw = [
            "01-02|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z",
        ]
        assert parser.parse_many(events_raw, step_id="01-01") == []

    def test_parse_many_skips_malformed_entries(self):
        parser = PhaseEventParser()
        events_raw = [
            "01-01|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z",
            "bad-data",
            "01-01|GREEN|EXECUTED|PASS|2026-02-02T10:10:00Z",
        ]
        result = parser.parse_many(events_raw, step_id="01-01")
        assert len(result) == 2

    def test_phase_event_is_frozen(self):
        event = PhaseEvent(
            "01-01", "PREPARE", "EXECUTED", "PASS", "2026-02-02T10:00:00Z"
        )
        with pytest.raises(AttributeError):
            event.status = "SKIPPED"  # type: ignore[misc]


# ===========================================================================
# MaxTurnsPolicy tests
# ===========================================================================


class TestMaxTurnsPolicy:
    """Tests for MaxTurnsPolicy.validate()."""

    @pytest.mark.parametrize("value", [10, 30, 50, 100])
    def test_validate_accepts_valid_range(self, value: int):
        policy = MaxTurnsPolicy()
        result = policy.validate(value)
        assert result.is_valid is True
        assert result.reason is None

    def test_validate_rejects_none(self):
        policy = MaxTurnsPolicy()
        result = policy.validate(None)
        assert result.is_valid is False
        assert "MISSING_MAX_TURNS" in result.reason

    @pytest.mark.parametrize("value", [0, 1, 9, 101, 200, -1])
    def test_validate_rejects_out_of_range(self, value: int):
        policy = MaxTurnsPolicy()
        result = policy.validate(value)
        assert result.is_valid is False
        assert "INVALID_MAX_TURNS" in result.reason
        assert str(value) in result.reason

    def test_validate_rejects_non_integer(self):
        policy = MaxTurnsPolicy()
        result = policy.validate("thirty")  # type: ignore[arg-type]
        assert result.is_valid is False
        assert "INVALID_MAX_TURNS" in result.reason

    def test_validate_rejects_float(self):
        policy = MaxTurnsPolicy()
        result = policy.validate(30.5)  # type: ignore[arg-type]
        assert result.is_valid is False

    def test_policy_result_is_frozen(self):
        result = PolicyResult(is_valid=True)
        with pytest.raises(AttributeError):
            result.is_valid = False  # type: ignore[misc]


# ===========================================================================
# DesMarkerParser tests
# ===========================================================================


class TestDesMarkerParser:
    """Tests for DesMarkerParser.parse()."""

    def test_parse_detects_des_validation_marker(self):
        parser = DesMarkerParser()
        result = parser.parse("Some text <!-- DES-VALIDATION : required --> more text")
        assert result.is_des_task is True

    def test_parse_returns_false_without_des_marker(self):
        parser = DesMarkerParser()
        result = parser.parse("Just a normal prompt without markers")
        assert result.is_des_task is False
        assert result.is_orchestrator_mode is False
        assert result.project_id is None
        assert result.step_id is None

    def test_parse_detects_orchestrator_mode(self):
        parser = DesMarkerParser()
        result = parser.parse(
            "<!-- DES-VALIDATION : required -->\n<!-- DES-MODE : orchestrator -->"
        )
        assert result.is_des_task is True
        assert result.is_orchestrator_mode is True

    def test_parse_extracts_project_id(self):
        parser = DesMarkerParser()
        result = parser.parse("<!-- DES-PROJECT-ID : my-project -->")
        assert result.project_id == "my-project"

    def test_parse_extracts_step_id(self):
        parser = DesMarkerParser()
        result = parser.parse("<!-- DES-STEP-ID : 01-03 -->")
        assert result.step_id == "01-03"

    def test_parse_handles_varied_whitespace(self):
        parser = DesMarkerParser()
        result = parser.parse("<!--DES-VALIDATION:required-->")
        assert result.is_des_task is True

    def test_parse_full_prompt_with_all_markers(self):
        parser = DesMarkerParser()
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            "<!-- DES-MODE : orchestrator -->\n"
            "<!-- DES-PROJECT-ID : auth-upgrade -->\n"
            "<!-- DES-STEP-ID : 02-01 -->\n"
            "Some prompt content..."
        )
        result = parser.parse(prompt)

        assert result.is_des_task is True
        assert result.is_orchestrator_mode is True
        assert result.project_id == "auth-upgrade"
        assert result.step_id == "02-01"

    def test_des_markers_is_frozen(self):
        markers = DesMarkers(is_des_task=True, is_orchestrator_mode=False)
        with pytest.raises(AttributeError):
            markers.is_des_task = False  # type: ignore[misc]


# ===========================================================================
# StepCompletionValidator tests
# ===========================================================================


class TestStepCompletionValidator:
    """Tests for StepCompletionValidator.validate()."""

    def test_validate_all_phases_passing(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()

        result = validator.validate(events)

        assert result.is_valid is True
        assert result.missing_phases == []
        assert result.incomplete_phases == []
        assert result.invalid_skips == []

    def test_validate_empty_events_returns_silent_completion(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)

        result = validator.validate([])

        assert result.is_valid is False
        assert result.error_type == "SILENT_COMPLETION"
        assert any("without updating" in msg for msg in result.error_messages)

    def test_validate_missing_phases_returns_abandoned(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        # Only 3 of 5 phases (missing GREEN and COMMIT)
        events = [
            _make_event("PREPARE"),
            _make_event("RED_ACCEPTANCE"),
            _make_event("RED_UNIT"),
        ]

        result = validator.validate(events)

        assert result.is_valid is False
        assert "GREEN" in result.missing_phases
        assert "COMMIT" in result.missing_phases
        assert result.error_type == "ABANDONED_PHASE"

    def test_validate_executed_with_invalid_outcome(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        # Replace GREEN with invalid outcome
        events[3] = _make_event("GREEN", status="EXECUTED", outcome="PARTIAL")

        result = validator.validate(events)

        assert result.is_valid is False
        assert "GREEN" in result.incomplete_phases
        assert result.error_type == "INCOMPLETE_PHASE"

    def test_validate_terminal_phase_must_pass(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        # COMMIT (terminal) with FAIL outcome
        events[4] = _make_event("COMMIT", status="EXECUTED", outcome="FAIL")

        result = validator.validate(events)

        assert result.is_valid is False
        assert "COMMIT" in result.incomplete_phases
        assert any("Terminal phase" in msg for msg in result.error_messages)

    def test_validate_skipped_with_valid_prefix(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        # GREEN skipped with valid prefix
        events[3] = _make_event(
            "GREEN",
            status="SKIPPED",
            outcome="NOT_APPLICABLE: No unit tests for config-only change",
        )

        result = validator.validate(events)

        assert result.is_valid is True

    def test_validate_skipped_with_invalid_prefix(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        events[3] = _make_event(
            "GREEN",
            status="SKIPPED",
            outcome="RANDOM_REASON: I just skipped it",
        )

        result = validator.validate(events)

        assert result.is_valid is False
        assert "GREEN" in result.invalid_skips
        assert result.error_type == "INVALID_SKIP"

    def test_validate_skipped_with_blocking_prefix(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        events[3] = _make_event(
            "GREEN",
            status="SKIPPED",
            outcome="DEFERRED: Will address in follow-up PR",
        )

        result = validator.validate(events)

        assert result.is_valid is False
        assert "GREEN" in result.invalid_skips
        assert any("DEFERRED" in msg for msg in result.error_messages)

    def test_validate_multiple_error_types(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = [
            _make_event("PREPARE"),
            _make_event("RED_ACCEPTANCE"),
            # RED_UNIT missing
            _make_event("GREEN", status="EXECUTED", outcome="PARTIAL"),
            _make_event("COMMIT"),
        ]

        result = validator.validate(events)

        assert result.is_valid is False
        assert result.error_type == "MULTIPLE_ERRORS"
        assert "RED_UNIT" in result.missing_phases
        assert "GREEN" in result.incomplete_phases

    def test_validate_invalid_status(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        events[2] = _make_event("RED_UNIT", status="UNKNOWN_STATUS", outcome="")

        result = validator.validate(events)

        assert result.is_valid is False
        assert any("Invalid status" in msg for msg in result.error_messages)

    def test_validate_recovery_suggestions_for_missing_phases(self):
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = [_make_event("PREPARE")]

        result = validator.validate(events)

        assert result.is_valid is False
        assert len(result.recovery_suggestions) > 0
        assert any("Resume" in s for s in result.recovery_suggestions)

    def test_completion_result_is_frozen(self):
        result = CompletionResult(is_valid=True)
        with pytest.raises(AttributeError):
            result.is_valid = False  # type: ignore[misc]

    def test_validate_non_terminal_phase_can_fail(self):
        """Non-terminal phases like GREEN can have FAIL outcome and still be valid."""
        schema = _make_schema()
        validator = StepCompletionValidator(schema)
        events = _make_all_passing_events()
        # GREEN with FAIL is valid (non-terminal)
        events[3] = _make_event("GREEN", status="EXECUTED", outcome="FAIL")

        result = validator.validate(events)

        # GREEN FAIL is valid - only COMMIT (terminal) must PASS
        assert result.is_valid is True
