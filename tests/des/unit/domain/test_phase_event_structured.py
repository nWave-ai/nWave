"""Unit tests for PhaseEventParser structured format parsing (v3.0).

Tests parse_structured() for dict-based events and parse_auto() for
automatic detection of string vs dict event formats.

Test Budget: 3 behaviors x 2 = 6 max tests. Using 5.
- parse_structured: basic dict -> PhaseEvent (1 test, parametrized)
- parse_structured with stats: dict with tu/tk -> PhaseEvent with stats (1 test)
- parse_auto: auto-detects string vs dict (1 parametrized test + 1 edge case)
- parse_structured invalid: missing keys -> None (1 test)
"""

from __future__ import annotations

import pytest

from des.domain.phase_event import PhaseEventParser


class TestParseStructured:
    """PhaseEventParser.parse_structured() converts dicts to PhaseEvent."""

    @pytest.mark.parametrize(
        "event_dict,expected_step,expected_phase,expected_status,expected_outcome",
        [
            (
                {
                    "sid": "08-01",
                    "p": "GREEN",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:00:00Z",
                },
                "08-01",
                "GREEN",
                "EXECUTED",
                "PASS",
            ),
            (
                {
                    "sid": "01-01",
                    "p": "RED_ACCEPTANCE",
                    "s": "SKIPPED",
                    "d": "NOT_APPLICABLE: no test framework",
                    "t": "2026-02-11T10:05:00Z",
                },
                "01-01",
                "RED_ACCEPTANCE",
                "SKIPPED",
                "NOT_APPLICABLE: no test framework",
            ),
        ],
        ids=["executed-pass", "skipped-with-reason"],
    )
    def test_parse_structured_returns_phase_event(
        self,
        event_dict,
        expected_step,
        expected_phase,
        expected_status,
        expected_outcome,
    ):
        """Parser converts structured dict with short keys to PhaseEvent."""
        parser = PhaseEventParser()
        event = parser.parse_structured(event_dict)

        assert event is not None
        assert event.step_id == expected_step
        assert event.phase_name == expected_phase
        assert event.status == expected_status
        assert event.outcome == expected_outcome
        assert event.turns_used is None
        assert event.tokens_used is None

    def test_parse_structured_extracts_stats(self):
        """Parser extracts tu and tk as turns_used and tokens_used."""
        parser = PhaseEventParser()
        event = parser.parse_structured(
            {
                "sid": "08-01",
                "p": "COMMIT",
                "s": "EXECUTED",
                "d": "PASS",
                "t": "2026-02-11T10:30:00Z",
                "tu": 25,
                "tk": 80000,
            }
        )

        assert event is not None
        assert event.turns_used == 25
        assert event.tokens_used == 80000

    def test_parse_structured_returns_none_for_missing_keys(self):
        """Parser returns None when required keys are missing from dict."""
        parser = PhaseEventParser()
        event = parser.parse_structured({"sid": "08-01", "p": "GREEN"})
        assert event is None


class TestParseAuto:
    """PhaseEventParser.parse_auto() detects string vs dict format."""

    @pytest.mark.parametrize(
        "event_input,expected_phase",
        [
            (
                "08-01|GREEN|EXECUTED|PASS|2026-02-11T10:00:00Z",
                "GREEN",
            ),
            (
                {
                    "sid": "08-01",
                    "p": "COMMIT",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:30:00Z",
                },
                "COMMIT",
            ),
        ],
        ids=["pipe-string", "structured-dict"],
    )
    def test_parse_auto_detects_format(self, event_input, expected_phase):
        """parse_auto correctly routes string to parse() and dict to parse_structured()."""
        parser = PhaseEventParser()
        event = parser.parse_auto(event_input)

        assert event is not None
        assert event.phase_name == expected_phase

    def test_parse_auto_returns_none_for_unsupported_type(self):
        """parse_auto returns None for non-string, non-dict input."""
        parser = PhaseEventParser()
        event = parser.parse_auto(12345)
        assert event is None
