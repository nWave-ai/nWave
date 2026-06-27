"""Regression tests for issue #50 — DDD→DDR column rename.

The 'DDD' column header in feature-delta commitment tables collided with the
dominant industry meaning of DDD (Domain-Driven Design), causing reviewer
agents to misread the traceability column. The column, its cell-reference
token, and the schema concept are renamed to DDR ("Design Decision Record").

Back-compat contract (deprecation window): legacy 'DDD' headers and 'DDD-N'
citations MUST still validate so existing feature-delta.md files do not break
on upgrade.

Behaviors:
  B1 — scaffold emits the DDR column header (not DDD)
  B2 — E2 accepts a DDR header (new canonical)
  B3 — E2 accepts a legacy DDD header (back-compat)
  B4 — E2 still flags a table missing the decision column entirely
  B5 — E4 v1.1 accepts a DDR-N citation
  B6 — E4 v1.1 accepts a legacy DDD-N citation (back-compat)
  B7 — parser reads both '- DDR-N:' and '- DDD-N:' design-decision bullets
  B8 — the migrator normalizes a legacy DDD delta to DDR
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.feature_delta.cli import init_scaffold_command
from nwave_ai.feature_delta.domain.model import (
    CommitmentRow,
    FeatureDeltaModel,
    WaveSection,
)
from nwave_ai.feature_delta.domain.parser import MarkdownSectionParser
from nwave_ai.feature_delta.domain.rules import e2_columns_present
from nwave_ai.feature_delta.domain.rules.e4_substantive_impact import check_v1_1


if TYPE_CHECKING:
    from pathlib import Path


_VERBS: tuple[str, ...] = ("ratifies", "preserves", "removes")


def _ddr_header(decision_col: str) -> str:
    return (
        "# f\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | {decision_col} | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | a commitment | n/a | an impact here |\n"
    )


def _model_with_impact(impact: str) -> FeatureDeltaModel:
    row = CommitmentRow(origin="DISCUSS#row1", commitment="c", ddr="n/a", impact=impact)
    section = WaveSection(name="DESIGN", rows=(row,), ddr_entries=())
    return FeatureDeltaModel(feature_id="t", sections=(section,))


# B1 — scaffold emits DDR ------------------------------------------------------


def test_scaffold_emits_ddr_column(tmp_path: Path) -> None:
    init_scaffold_command("ddr-feature", output_dir=tmp_path)
    content = (
        tmp_path / "docs" / "feature" / "ddr-feature" / "feature-delta.md"
    ).read_text()
    assert "| Origin | Commitment | DDR | Impact |" in content
    assert "| DDD |" not in content


# B2/B3 — E2 accepts DDR (new) and DDD (legacy) --------------------------------


def test_e2_accepts_ddr_header() -> None:
    violations = e2_columns_present.check(_ddr_header("DDR"), "f.md")
    assert violations == ()


def test_e2_accepts_legacy_ddd_header_backcompat() -> None:
    violations = e2_columns_present.check(_ddr_header("DDD"), "f.md")
    assert violations == ()


# B4 — E2 still flags a missing decision column --------------------------------


def test_e2_flags_table_missing_decision_column() -> None:
    text = (
        "# f\n\n## Wave: DESIGN\n\n### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | Impact |\n"
        "|--------|------------|--------|\n"
        "| n/a | c | i |\n"
    )
    violations = e2_columns_present.check(text, "f.md")
    assert len(violations) >= 1
    assert violations[0].rule == "E2"
    assert "DDR" in violations[0].remediation


# B5/B6 — E4 accepts DDR-N (new) and DDD-N (legacy) ----------------------------


def test_e4_accepts_ddr_citation() -> None:
    model = _model_with_impact("DDR-1 ratifies the relaxation")
    assert check_v1_1(model, _VERBS) == ()


def test_e4_accepts_legacy_ddd_citation_backcompat() -> None:
    model = _model_with_impact("DDD-1 ratifies the relaxation")
    assert check_v1_1(model, _VERBS) == ()


# B7 — parser reads DDR-N and DDD-N design-decision bullets --------------------


def _delta_with_bullet(token: str) -> str:
    return (
        "# f\n\n## Wave: DESIGN\n\n"
        "### [REF] Design Decisions\n\n"
        f"- {token}: authorize the removal\n"
    )


def test_parser_reads_ddr_bullet() -> None:
    model = MarkdownSectionParser().parse(_delta_with_bullet("DDR-1"))
    design = next(s for s in model.sections if s.name == "DESIGN")
    assert len(design.ddr_entries) == 1
    assert design.ddr_entries[0].number == 1


def test_parser_reads_legacy_ddd_bullet_backcompat() -> None:
    model = MarkdownSectionParser().parse(_delta_with_bullet("DDD-2"))
    design = next(s for s in model.sections if s.name == "DESIGN")
    assert len(design.ddr_entries) == 1
    assert design.ddr_entries[0].number == 2


# B8 — migrator normalizes legacy DDD → DDR -----------------------------------


def test_normalize_rewrites_legacy_ddd_to_ddr() -> None:
    from nwave_ai.feature_delta.domain.normalize import normalize_decision_refs

    legacy = (
        "# f\n\n## Wave: DESIGN\n\n### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | c | DDD-1 | DDD-1 ratifies the change |\n\n"
        "### [REF] Design Decisions\n\n"
        "- DDD-1: authorize the removal\n"
    )
    out = normalize_decision_refs(legacy)
    assert "| Origin | Commitment | DDR | Impact |" in out
    assert "DDR-1" in out
    assert "DDD-1" not in out
    assert "| DDD |" not in out
    # Idempotent: normalizing an already-DDR document is a no-op.
    assert normalize_decision_refs(out) == out


# B9 — migrate-feature command normalizes a legacy DDD delta on disk ----------


def test_migrate_feature_command_normalizes_delta(tmp_path: Path) -> None:
    from nwave_ai.feature_delta.cli import migrate_feature_command

    fdir = tmp_path / "legacy-feature"
    fdir.mkdir()
    (fdir / "feature-delta.md").write_text(
        "# legacy-feature\n\n## Wave: DESIGN\n\n### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | c | DDD-1 | DDD-1 ratifies the change |\n",
        encoding="utf-8",
    )

    exit_code = migrate_feature_command(str(fdir))

    assert exit_code == 0
    content = (fdir / "feature-delta.md").read_text(encoding="utf-8")
    assert "| Origin | Commitment | DDR | Impact |" in content
    assert "DDD" not in content
