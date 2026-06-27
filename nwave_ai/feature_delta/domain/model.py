"""FeatureDeltaModel and value objects."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommitmentRow:
    origin: str
    commitment: str
    ddr: str
    impact: str


@dataclass(frozen=True)
class DDREntry:
    number: int
    text: str


@dataclass(frozen=True)
class WaveSection:
    name: str
    rows: tuple[CommitmentRow, ...]
    ddr_entries: tuple[DDREntry, ...]
    gherkin_blocks: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FeatureDeltaModel:
    feature_id: str
    sections: tuple[WaveSection, ...]
