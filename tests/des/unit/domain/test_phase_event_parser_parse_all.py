"""Unit tests for PhaseEventParser.parse_all() (UT-11 through UT-13)."""

from des.domain.phase_event import PhaseEventParser


class TestParseAll:
    """Tests for the new parse_all() method."""

    def test_parse_all_returns_all_events_unfiltered(self) -> None:
        """UT-11: parse_all returns events for all step_ids."""
        parser = PhaseEventParser()
        events = parser.parse_all(
            [
                "01-01|PREPARE|EXECUTED|PASS|2026-02-10T12:00:00Z",
                "01-02|PREPARE|EXECUTED|PASS|2026-02-10T12:01:00Z",
                "01-03|RED_ACCEPTANCE|EXECUTED|FAIL|2026-02-10T12:02:00Z",
            ]
        )
        assert len(events) == 3
        assert events[0].step_id == "01-01"
        assert events[1].step_id == "01-02"
        assert events[2].step_id == "01-03"

    def test_parse_all_skips_malformed_entries(self) -> None:
        """UT-12: parse_all silently skips malformed entries."""
        parser = PhaseEventParser()
        events = parser.parse_all(
            [
                "01-01|PREPARE|EXECUTED|PASS|2026-02-10T12:00:00Z",
                "malformed",
                "too|few|fields",
                "01-02|COMMIT|EXECUTED|PASS|2026-02-10T12:03:00Z",
            ]
        )
        assert len(events) == 2
        assert events[0].step_id == "01-01"
        assert events[1].step_id == "01-02"

    def test_parse_all_empty_list_returns_empty(self) -> None:
        """UT-13: parse_all with empty input returns empty list."""
        parser = PhaseEventParser()
        events = parser.parse_all([])
        assert events == []
