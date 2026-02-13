"""Unit tests for verify_deliver_integrity CLI step extraction and log parsing."""

from des.cli.verify_deliver_integrity import _extract_step_ids, _parse_execution_log


class TestExtractStepIds:
    """Tests for _extract_step_ids supporting both roadmap formats."""

    def test_flat_format_with_step_id_key(self):
        """Flat roadmap with top-level 'steps' using 'step_id' keys."""
        roadmap = {
            "steps": [
                {"step_id": "01-01", "name": "First"},
                {"step_id": "01-02", "name": "Second"},
            ]
        }
        assert _extract_step_ids(roadmap) == ["01-01", "01-02"]

    def test_flat_format_with_id_key(self):
        """Flat roadmap with top-level 'steps' using 'id' keys."""
        roadmap = {
            "steps": [
                {"id": "01-01"},
                {"id": "02-01"},
            ]
        }
        assert _extract_step_ids(roadmap) == ["01-01", "02-01"]

    def test_nested_format_with_phases(self):
        """Nested roadmap with 'phases' containing 'steps'."""
        roadmap = {
            "phases": [
                {
                    "phase_id": "01",
                    "steps": [
                        {"step_id": "01-01"},
                        {"step_id": "01-02"},
                    ],
                },
                {
                    "phase_id": "02",
                    "steps": [
                        {"step_id": "02-01"},
                    ],
                },
            ]
        }
        assert _extract_step_ids(roadmap) == ["01-01", "01-02", "02-01"]

    def test_nested_format_with_id_key(self):
        """Nested roadmap using 'id' instead of 'step_id'."""
        roadmap = {
            "phases": [
                {
                    "phase_id": "01",
                    "steps": [{"id": "01-01"}],
                },
            ]
        }
        assert _extract_step_ids(roadmap) == ["01-01"]

    def test_empty_roadmap_returns_empty(self):
        """Roadmap with no steps or phases returns empty list."""
        assert _extract_step_ids({}) == []

    def test_phases_with_no_steps_returns_empty(self):
        """Phases without steps key returns empty list."""
        roadmap = {"phases": [{"phase_id": "01"}]}
        assert _extract_step_ids(roadmap) == []

    def test_flat_format_takes_priority(self):
        """If both 'steps' and 'phases' exist, flat 'steps' wins."""
        roadmap = {
            "steps": [{"step_id": "flat-01"}],
            "phases": [
                {"steps": [{"step_id": "nested-01"}]},
            ],
        }
        assert _extract_step_ids(roadmap) == ["flat-01"]


class TestParseExecutionLog:
    """Tests for _parse_execution_log supporting v2.0 and v3.0 formats."""

    def test_v2_pipe_format(self):
        """v2.0 pipe-delimited format: 'step|phase|status|data|ts'."""
        log = {
            "events": [
                "01-01|PREPARE|EXECUTED|PASS|2026-01-01T00:00:00Z",
                "01-01|GREEN|EXECUTED|PASS|2026-01-01T00:01:00Z",
            ]
        }
        result = _parse_execution_log(log)
        assert result == {"01-01": ["PREPARE", "GREEN"]}

    def test_v3_structured_format(self):
        """v3.0 structured dict format: {sid, p, s, d, t}."""
        log = {
            "events": [
                {"sid": "02-01", "p": "PREPARE", "s": "EXECUTED", "d": "PASS"},
                {"sid": "02-01", "p": "COMMIT", "s": "EXECUTED", "d": "PASS"},
            ]
        }
        result = _parse_execution_log(log)
        assert result == {"02-01": ["PREPARE", "COMMIT"]}

    def test_mixed_formats(self):
        """Log with both v2.0 and v3.0 events."""
        log = {
            "events": [
                "01-01|PREPARE|EXECUTED|PASS|2026-01-01T00:00:00Z",
                {"sid": "01-01", "p": "GREEN", "s": "EXECUTED", "d": "PASS"},
            ]
        }
        result = _parse_execution_log(log)
        assert result == {"01-01": ["PREPARE", "GREEN"]}

    def test_empty_events(self):
        """Empty events list returns empty dict."""
        assert _parse_execution_log({"events": []}) == {}

    def test_no_events_key(self):
        """Missing events key returns empty dict."""
        assert _parse_execution_log({}) == {}
