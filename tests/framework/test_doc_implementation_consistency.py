"""Fitness function: doc-claims vs impl-default consistency for canon migration.

CONTRACT_SHAPE: pure-function
Outcome anchor: After running test suite, developers see doc-claims-vs-impl-default
drift fails CI immediately, not in user reports.

Asserts that the documented default canon (declared in
``nWave/templates/step-tdd-cycle-schema.json:canon_migration.default_for_new_logs``)
matches the runtime defaults exposed by:
1. ``TDDSchemaLoader().load().tdd_phases`` (active phase list getter)
2. ``DESConfig().rigor_tdd_phases`` (fallback default tuple)

Generalizes the pattern shipped in ``test_skill_command_consistency.py`` (#52,
commit 0d8803030): same architectural family — fitness function for the
doc-claims-vs-impl-default drift class. Parametrize allows future extension to
additional invariants without churning the test structure.

Empirical anchor: RCA at docs/feature/fix-des-canon-default-migration/. Schema
claims ``default_for_new_logs == "v5"`` (3-phase canon per ADR-025) but both
runtime defaults still return the legacy 5-phase list — drift that the prior
test suite cemented rather than exposed (RC-D).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from des.adapters.driven.config.des_config import DESConfig
from des.domain.tdd_schema import CANONICAL_PHASES, LEGACY_PHASES, TDDSchemaLoader


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "nWave" / "templates" / "step-tdd-cycle-schema.json"
ADR_025_PATH = REPO_ROOT / "docs" / "architecture" / "ADR-025-3-phase-tdd-canon.md"

# Bidirectional crossref locations: files that MUST cite "ADR-025" so any reader
# of those modules can resolve the canonical decision record. Closes RC-C from
# RCA (docs/feature/fix-des-canon-default-migration/discuss/wave-decisions.md):
# previously the ADR file was missing, so every cite from these locations was
# a broken reference. Step 01-04 (F5) authors the ADR + locks both directions.
ADR_025_BACKLINK_LOCATIONS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "des" / "domain" / "tdd_schema.py",
    REPO_ROOT / "src" / "des" / "application" / "validator.py",
    REPO_ROOT / "nWave" / "skills" / "nw-tdd-methodology" / "SKILL.md",
    REPO_ROOT / "nWave" / "skills" / "nw-deliver" / "SKILL.md",
    REPO_ROOT / "nWave" / "skills" / "nw-rigor" / "SKILL.md",
)

# Required ADR template sections (per nWave ADR precedent ADR-PLAT-001..006 +
# reviewer Revision 2 of step 01-04 acceptance criteria). Grep for the markdown
# header line at any heading depth — section presence, not depth, is the
# contract.
ADR_025_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Title",  # the ADR's title line itself ("ADR-025: ...")
    "Status",
    "Context",
    "Decision",
    "Rationale",
    "Alternatives",
    "Consequences",
    "Related Decisions",
)

CANON_VERSION_TO_PHASES: dict[str, tuple[str, ...]] = {
    "v5": CANONICAL_PHASES,
    "v4": LEGACY_PHASES,
}


def _documented_default_phases() -> tuple[str, ...]:
    """Read the schema's documented ``default_for_new_logs`` and map to phases."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        raw_schema = json.load(f)
    documented = raw_schema["canon_migration"]["default_for_new_logs"]
    assert documented in CANON_VERSION_TO_PHASES, (
        f"Schema canon_migration.default_for_new_logs={documented!r} is not a "
        f"recognised canon version. Expected one of {sorted(CANON_VERSION_TO_PHASES)}."
    )
    return CANON_VERSION_TO_PHASES[documented]


def test_schema_default_canon_matches_documented_intent() -> None:
    """TDDSchemaLoader().load().tdd_phases must match the documented default.

    The schema's ``canon_migration.default_for_new_logs`` field is the SSOT
    declaration of which canon the framework defaults to. The loader's
    ``tdd_phases`` getter is the runtime accessor production code consults
    for the active phase list. When these two disagree, doc claims one canon
    while impl returns another — that drift breaks audit-log consumers and
    misleads agent skill loading.
    """
    documented = _documented_default_phases()
    runtime = TDDSchemaLoader().load().tdd_phases
    assert runtime == documented, (
        f"Doc-impl drift detected: schema documents default_for_new_logs as "
        f"phases={documented!r} (v5 canonical per ADR-025), but "
        f"TDDSchemaLoader().load().tdd_phases returns {runtime!r} "
        f"(legacy v4 5-phase). The active getter must follow the documented "
        f"default."
    )


def test_des_config_rigor_phases_default_matches_documented_intent() -> None:
    """DESConfig().rigor_tdd_phases must default to the documented canon.

    When the project has no ``.nwave/des-config.json`` and no global rigor
    overrides, ``rigor_tdd_phases`` returns its hardcoded fallback tuple.
    That fallback is what every greenfield project sees on first run — it
    MUST match the documented canon, otherwise new projects start on the
    legacy canon while the schema claims v5.
    """
    documented = _documented_default_phases()
    runtime = DESConfig(
        config_path=Path("/nonexistent/des-config.json"),
        global_config_path=Path("/nonexistent/global-config.json"),
    ).rigor_tdd_phases
    assert runtime == documented, (
        f"Doc-impl drift detected: schema documents default_for_new_logs as "
        f"phases={documented!r} (v5 canonical per ADR-025), but "
        f"DESConfig().rigor_tdd_phases falls back to {runtime!r} "
        f"(legacy v4 5-phase). Greenfield projects must default to the "
        f"documented canon."
    )


@pytest.mark.parametrize(
    "invariant_name",
    [
        "schema_default_canon",
        "des_config_rigor_phases",
    ],
)
def test_documented_canon_is_a_recognised_version(invariant_name: str) -> None:
    """Sanity gate: the schema's documented canon resolves to a known phase set.

    Parametrized over the invariant labels for future extension — when a third
    surface (e.g. orchestrator default, agent template) needs the same parity
    check, add the label here and write a focused test above. Keeps the
    fitness function generic and extensible without test inflation.
    """
    del invariant_name  # label is documentation; resolution is shared
    documented = _documented_default_phases()
    assert documented in (CANONICAL_PHASES, LEGACY_PHASES), (
        f"Schema documented default resolved to {documented!r}, which is "
        f"neither CANONICAL_PHASES nor LEGACY_PHASES. Add the new canon to "
        f"CANON_VERSION_TO_PHASES."
    )


def test_adr_025_exists_with_required_sections_and_bidirectional_crossrefs() -> None:
    """ADR-025 file must exist, contain required sections, and crossref bidirectionally.

    Closes RC-C from RCA (docs/feature/fix-des-canon-default-migration/discuss/
    wave-decisions.md). The schema's ``canon_migration.adr`` field (set to
    ``"ADR-025"``) cites a decision record; that record must (a) exist on
    disk, (b) follow the nWave ADR template (Title/Status/Context/Decision/
    Rationale/Alternatives/Consequences/Related Decisions sections present),
    and (c) be cited back from the code modules and skill docs that implement
    the decision, so Earned Trust is preserved: every reference resolves and
    every consumer back-links to the authority.

    Single test covering 3 invariants (file existence, sections present,
    bidirectional crossref parity) — one test per behavior per the test
    budget. The error messages distinguish which invariant tripped so a
    failure points the author at the right artefact.
    """
    # Invariant 1: ADR file exists at the expected path.
    assert ADR_025_PATH.exists(), (
        f"ADR-025 missing at {ADR_025_PATH.relative_to(REPO_ROOT)}. The "
        f"schema's canon_migration.adr field cites it but the file does not "
        f"exist — every reference from code/docs to ADR-025 is broken. "
        f"Author the record per nWave ADR template (see "
        f"docs/product/architecture/ADR-PLAT-004-orchestrator-decomposition.md "
        f"for style reference)."
    )

    # Invariant 2: ADR contains required template sections (markdown headers).
    adr_text = ADR_025_PATH.read_text(encoding="utf-8")
    missing_sections = [
        section
        for section in ADR_025_REQUIRED_SECTIONS
        if not _markdown_section_present(adr_text, section)
    ]
    assert not missing_sections, (
        f"ADR-025 is missing required template sections: {missing_sections}. "
        f"Each section must appear as a markdown header (any depth) in "
        f"{ADR_025_PATH.relative_to(REPO_ROOT)}. Required sections per "
        f"nWave ADR precedent (ADR-PLAT-001..006) + reviewer Revision 2: "
        f"{list(ADR_025_REQUIRED_SECTIONS)}."
    )

    # Invariant 3: bidirectional crossref — schema cites ADR-025, AND every
    # listed code/skill location cites ADR-025 back. Forward direction was
    # already established by step 01-01; this test locks the back direction.
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema_doc = json.load(f)
    schema_cite = schema_doc.get("canon_migration", {}).get("adr", "")
    assert schema_cite == "ADR-025", (
        f"Schema canon_migration.adr field should cite 'ADR-025' (forward "
        f"crossref), got {schema_cite!r}. Forward direction broken — fix "
        f"{SCHEMA_PATH.relative_to(REPO_ROOT)}."
    )
    missing_backlinks = [
        location.relative_to(REPO_ROOT).as_posix()
        for location in ADR_025_BACKLINK_LOCATIONS
        if not _file_cites_adr_025(location)
    ]
    assert not missing_backlinks, (
        f"ADR-025 backlinks missing from {len(missing_backlinks)} location(s): "
        f"{missing_backlinks}. Each implementing module/skill must cite "
        f"'ADR-025' so a reader of that file can follow the back-link to "
        f"the authoritative decision record. Bidirectional crossref is the "
        f"Earned Trust contract."
    )


def _markdown_section_present(adr_text: str, section: str) -> bool:
    """Return True if ``section`` appears as a markdown header line in ``adr_text``.

    Accepts any heading depth (``#`` through ``######``) so the ADR author can
    structure the document freely as long as the section label is reachable
    via grep. The "Title" sentinel is treated specially — it matches the
    document's opening ``# ADR-025`` line.
    """
    if section == "Title":
        return any(
            line.startswith("# ") and "ADR-025" in line
            for line in adr_text.splitlines()
        )
    for line in adr_text.splitlines():
        stripped = line.lstrip("#").strip()
        if stripped == section and line.startswith("#"):
            return True
    return False


def _file_cites_adr_025(path: Path) -> bool:
    """Return True if ``path`` contains the literal token ``"ADR-025"``.

    Substring match (not regex) — the goal is "any human reader of this file
    can find the back-link via Ctrl-F", which is the bidirectional-crossref
    contract.
    """
    if not path.exists():
        return False
    return "ADR-025" in path.read_text(encoding="utf-8")
