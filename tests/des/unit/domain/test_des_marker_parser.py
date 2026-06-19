"""Tests for DesMarkerParser DES-PROJECT-ROOT marker support.

Outcome anchor: DISCUSS "orchestrator dispatching crafter on a worktree sees
correct audit-trail validation, not stale-master false-positive halts."

The parser exposes a new field `project_root` which carries the worktree-rooted
project path so hooks can resolve execution-log against the correct repo when
the orchestrator's CWD differs from the worktree (Rex RCA Option A).

CONTRACT_SHAPE: pure-function
Universe: parsed-context dict (return value of DesMarkerParser.parse).
"""

from __future__ import annotations

import pytest

from des.domain.des_marker_parser import DesMarkerParser, DesMarkers


class TestProjectRootMarkerParsing:
    """Parser recognises DES-PROJECT-ROOT and emits parsed field."""

    def test_extracts_project_root_when_marker_present(self):
        """Marker value MUST surface in DesMarkers.project_root."""
        parser = DesMarkerParser()
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            "<!-- DES-PROJECT-ID : my-feat -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "<!-- DES-PROJECT-ROOT : /worktrees/my-feat -->\n"
            "Execute step"
        )

        result = parser.parse(prompt)

        assert result.project_root == "/worktrees/my-feat"

    def test_project_root_is_none_when_marker_absent(self):
        """Backward compat: when marker absent, project_root is None."""
        parser = DesMarkerParser()
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            "<!-- DES-PROJECT-ID : my-feat -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "Execute step"
        )

        result = parser.parse(prompt)

        assert result.project_root is None

    @pytest.mark.parametrize(
        "marker_line,expected",
        [
            ("<!--DES-PROJECT-ROOT:/abs/path-->", "/abs/path"),
            ("<!-- DES-PROJECT-ROOT:/abs/path -->", "/abs/path"),
            ("<!--   DES-PROJECT-ROOT   :   /abs/path   -->", "/abs/path"),
        ],
    )
    def test_parser_handles_varied_whitespace_around_marker(
        self, marker_line, expected
    ):
        """Same whitespace tolerance as other DES markers."""
        parser = DesMarkerParser()
        prompt = f"<!-- DES-VALIDATION : required -->\n{marker_line}\n"

        result = parser.parse(prompt)

        assert result.project_root == expected

    def test_des_markers_dataclass_frozen_includes_project_root(self):
        """Frozen invariant preserved with new field."""
        markers = DesMarkers(
            is_des_task=True,
            is_orchestrator_mode=False,
            project_id="x",
            step_id="01-01",
            project_root="/path",
        )
        with pytest.raises(AttributeError):
            markers.project_root = "/other"  # type: ignore[misc]
