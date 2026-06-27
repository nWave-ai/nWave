"""MarkdownSectionParser — line-state machine for feature-delta.md."""

from __future__ import annotations

import re

from nwave_ai.feature_delta.domain.model import (
    CommitmentRow,
    DDREntry,
    FeatureDeltaModel,
    WaveSection,
)


_WAVE_HEADING = re.compile(r"^##\s+Wave:\s+(\w+)")
_TABLE_SEPARATOR = re.compile(r"^\|[-|: ]+\|")
_TABLE_ROW = re.compile(r"^\|(.+)\|")
_DESIGN_DECISIONS_HEADING = re.compile(
    r"^###\s+\[REF\]\s+Design Decisions", re.IGNORECASE
)
# Design-decision bullet: DDR-N canonical; legacy DDD-N accepted (issue #50).
_DECISION_BULLET = re.compile(r"^-\s+DD[DR]-(\d+):\s+(.+)")

_HEADER_ROW = re.compile(r"^\|\s*Origin\s*\|", re.IGNORECASE)
_FENCED_GHERKIN_OPEN = re.compile(r"^```gherkin\s*$")
_FENCED_CLOSE = re.compile(r"^```\s*$")


def _parse_row(line: str) -> CommitmentRow | None:
    """Parse a pipe-delimited table data row into a CommitmentRow."""
    if _TABLE_SEPARATOR.match(line):
        return None
    if _HEADER_ROW.match(line):
        return None
    match = _TABLE_ROW.match(line)
    if not match:
        return None
    cells = [c.strip() for c in match.group(1).split("|")]
    if len(cells) < 4:
        return None
    return CommitmentRow(
        origin=cells[0],
        commitment=cells[1],
        ddr=cells[2],
        impact=cells[3],
    )


class MarkdownSectionParser:
    """Parse a feature-delta.md document into a FeatureDeltaModel.

    State machine states:
      OUTSIDE_WAVE          — before any ## Wave: heading
      IN_WAVE_HEADING       — just saw ## Wave: NAME
      IN_COMMITMENTS_TABLE  — inside ### [REF] Inherited commitments table
      IN_GHERKIN_BLOCK      — inside ```gherkin ... ``` fenced block
    """

    def parse(self, text: str) -> FeatureDeltaModel:
        sections: list[WaveSection] = []
        current_wave: str | None = None
        current_rows: list[CommitmentRow] = []
        current_ddr_entries: list[DDREntry] = []
        current_gherkin_blocks: list[str] = []
        in_table = False
        in_decision_section = False
        in_gherkin_block = False
        gherkin_block_lines: list[str] = []
        feature_id = ""

        for line in text.splitlines():
            # Feature title (first # heading)
            if line.startswith("# ") and not feature_id:
                feature_id = line[2:].strip()
                continue

            # Handle gherkin fenced block state (highest priority — spans headings)
            if in_gherkin_block:
                if _FENCED_CLOSE.match(line):
                    in_gherkin_block = False
                    current_gherkin_blocks.append("\n".join(gherkin_block_lines))
                    gherkin_block_lines = []
                else:
                    gherkin_block_lines.append(line)
                continue

            wave_match = _WAVE_HEADING.match(line)
            if wave_match:
                # Flush previous wave
                if current_wave is not None:
                    sections.append(
                        WaveSection(
                            name=current_wave,
                            rows=tuple(current_rows),
                            ddr_entries=tuple(current_ddr_entries),
                            gherkin_blocks=tuple(current_gherkin_blocks),
                        )
                    )
                current_wave = wave_match.group(1)
                current_rows = []
                current_ddr_entries = []
                current_gherkin_blocks = []
                in_table = False
                in_decision_section = False
                continue

            if current_wave is None:
                # Check for gherkin blocks before first wave heading too
                if _FENCED_GHERKIN_OPEN.match(line):
                    in_gherkin_block = True
                    gherkin_block_lines = []
                continue

            # Detect gherkin fenced block open
            if _FENCED_GHERKIN_OPEN.match(line):
                in_gherkin_block = True
                gherkin_block_lines = []
                in_table = False
                in_decision_section = False
                continue

            if "### [REF] Inherited commitments" in line:
                in_table = True
                in_decision_section = False
                continue

            if _DESIGN_DECISIONS_HEADING.match(line):
                in_decision_section = True
                in_table = False
                continue

            if in_decision_section:
                decision_match = _DECISION_BULLET.match(line)
                if decision_match:
                    current_ddr_entries.append(
                        DDREntry(
                            number=int(decision_match.group(1)),
                            text=decision_match.group(2).strip(),
                        )
                    )
                continue

            if in_table and line.startswith("|"):
                row = _parse_row(line)
                if row is not None:
                    current_rows.append(row)
                continue

            # Blank line after table ends the table context only if we hit
            # another heading, not on every blank line (tables can have gaps).

        # Flush last wave
        if current_wave is not None:
            sections.append(
                WaveSection(
                    name=current_wave,
                    rows=tuple(current_rows),
                    ddr_entries=tuple(current_ddr_entries),
                    gherkin_blocks=tuple(current_gherkin_blocks),
                )
            )

        return FeatureDeltaModel(
            feature_id=feature_id or "unknown",
            sections=tuple(sections),
        )

    def probe(self) -> None:
        """Verify the parser is functional (startup health check)."""
        result = self.parse("# probe\n\n## Wave: PROBE\n")
        assert any(s.name == "PROBE" for s in result.sections)
