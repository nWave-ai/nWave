"""Unit tests for execution statistics fields in PhaseEvent and PhaseEventParser.

Tests that turns_used and tokens_used are correctly represented in PhaseEvent
and parsed from both 5-field (legacy) and 7-field (new) pipe-delimited formats.

Test Budget: 3 behaviors x 2 = 6 max tests. Using 4.
"""

from __future__ import annotations

import pytest

from des.domain.phase_event import PhaseEvent, PhaseEventParser


class TestPhaseEventExecStatsFields:
    """PhaseEvent dataclass carries optional execution statistics."""

    def test_phase_event_with_exec_stats(self):
        """PhaseEvent stores turns_used and tokens_used when provided."""
        event = PhaseEvent(
            step_id="07-01",
            phase_name="COMMIT",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-11T00:00:00Z",
            turns_used=12,
            tokens_used=45000,
        )
        assert event.turns_used == 12
        assert event.tokens_used == 45000

    def test_phase_event_defaults_stats_to_none(self):
        """PhaseEvent defaults turns_used and tokens_used to None (backward compat)."""
        event = PhaseEvent(
            step_id="07-01",
            phase_name="PREPARE",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-11T00:00:00Z",
        )
        assert event.turns_used is None
        assert event.tokens_used is None


class TestPhaseEventParserExecStats:
    """PhaseEventParser extracts execution statistics from pipe-delimited strings."""

    @pytest.mark.parametrize(
        "event_str,expected_turns,expected_tokens",
        [
            (
                "07-01|COMMIT|EXECUTED|PASS|2026-02-11T00:00:00Z|12|45000",
                12,
                45000,
            ),
            (
                "07-01|COMMIT|EXECUTED|PASS|2026-02-11T00:00:00Z|0|0",
                0,
                0,
            ),
        ],
        ids=["typical-stats", "zero-stats"],
    )
    def test_parse_extracts_stats_from_7_field_format(
        self, event_str, expected_turns, expected_tokens
    ):
        """Parser returns turns_used and tokens_used from 7-field entries."""
        parser = PhaseEventParser()
        event = parser.parse(event_str)

        assert event is not None
        assert event.turns_used == expected_turns
        assert event.tokens_used == expected_tokens

    def test_parse_returns_none_stats_for_5_field_format(self):
        """Parser returns None for turns_used/tokens_used in legacy 5-field entries."""
        parser = PhaseEventParser()
        event = parser.parse("07-01|PREPARE|EXECUTED|PASS|2026-02-11T00:00:00Z")

        assert event is not None
        assert event.turns_used is None
        assert event.tokens_used is None
