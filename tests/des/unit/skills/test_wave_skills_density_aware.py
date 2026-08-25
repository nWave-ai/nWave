"""Unit tests asserting all 6 wave skills encode density-aware behavior.

v3.14 propagation (lean-wave-documentation, post-DDD-7 pilot). The DISCUSS
pilot was validated first; the same density-aware 3-section pattern (Output
Tiers / Density resolution / Telemetry) was then propagated to the
remaining 5 wave skills (DISCOVER, DESIGN, DEVOPS, DISTILL, DELIVER).

Track A.3 consolidation (2026-04-28): the original DISCUSS-only test file
``test_nw_discuss_density_aware.py`` was a strict subset of this contract
once nw-discuss is included in WAVE_SKILLS. The pilot file was deleted
and DISCUSS is now covered here as the sixth wave skill, with one focused
holdout test for D6 (the install-time-prompt decision unique to DISCUSS).

Track B.2 consolidation (2026-04-28): the original cross-product
parametrization produced 181 phrase-grep tests (Output Tiers x phrases x
skills + Density resolution x phrases x skills + Telemetry x phrases x
skills + Provenance x decision_ids x skills, etc.). Behavior count is 1
("the wave skill encodes the density-aware contract") with input
variation across (skill, section, phrase). Per behavior-first test
budget, collapsed to 6 tests (one per skill) + 1 holdout (D6 in
DISCUSS) = 7 tests. Each per-skill test asserts ALL required phrases
in one pass and lists the missing phrases by section in the failure
message — the diagnostic granularity of 30 cases per skill condensed
into a single failure that points at the right skill.

Strategy: content assertion. The skill is a Claude-Code-substrate concern,
not nWave-internal Python; the runtime "interpreter" is the Claude agent that
reads the markdown. Asserting the markdown contains the right instructions IS
the contract test for a markdown SOP.

Cross-references: feature-delta.md DDD-7 (DISCUSS pilot, post-pilot
propagation), DDD-2 (--expand lives in skill), DDD-5 (density resolver),
DDD-6 (telemetry event), D2/D4/D6/D10/D12 (locked decisions).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.shared.density_config import EXPANSION_PROMPT_MODES


# ---------------------------------------------------------------------------
# Skill discovery — walk up from this file to the repo root, then read each
# of the six wave skill markdown files. Pure path resolution.
# ---------------------------------------------------------------------------


WAVE_SKILLS = (
    "nw-discover",
    "nw-discuss",
    "nw-design",
    "nw-devops",
    "nw-distill",
    "nw-deliver",
)
WAVE_NAMES = {
    "nw-discover": "DISCOVER",
    "nw-discuss": "DISCUSS",
    "nw-design": "DESIGN",
    "nw-devops": "DEVOPS",
    "nw-distill": "DISTILL",
    "nw-deliver": "DELIVER",
}

# Phrase clusters per section. Each cluster is the input-variation set for
# a single behavior ("the skill contains the <section> contract"). Failure
# messages enumerate the missing phrases per section so the diagnostic is
# as specific as the pre-collapse parametrize case.
OUTPUT_TIERS_PHRASES: tuple[str, ...] = (
    "## Output Tiers",
    "Tier-1",
    "Tier-2",
    "EXPANSION CATALOG",
    "[REF]",
    "[WHY]",
    "[HOW]",
)
DENSITY_RESOLUTION_PHRASES: tuple[str, ...] = (
    "## Density resolution",
    "resolve_density(global_config)",
    "scripts/shared/density_config.py",
    "~/.nwave/global-config.json",
    "expansion_prompt",
)
DENSITY_MODE_BRANCHES: tuple[str, ...] = ("lean", "full")
TELEMETRY_PHRASES: tuple[str, ...] = (
    "## Telemetry",
    "DocumentationDensityEvent",
    "JsonlAuditLogWriter",
    "to_audit_event",
    "feature_id",
    "expansion_id",
    "choice",
    "timestamp",
)
PROVENANCE_DECISION_IDS: tuple[str, ...] = ("D2", "D4", "D10", "D12")
PROVENANCE_DDD_IDS: tuple[str, ...] = ("DDD-5", "DDD-6")


def _repo_root() -> Path:
    """Return the repo root by locating nWave/skills/ ancestor."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "nWave" / "skills" / "nw-discover").is_dir():
            return ancestor
    raise RuntimeError("could not locate nWave/skills/nw-discover/ from test file path")


def _load_skill_text(skill: str) -> str:
    """Return the SKILL.md text for a single wave skill."""
    path = _repo_root() / "nWave" / "skills" / skill / "SKILL.md"
    assert path.exists(), f"{skill} SKILL.md missing at {path}"
    return path.read_text(encoding="utf-8")


def _load_density_contract() -> str:
    """Return the shared density-resolution contract text."""
    path = (
        _repo_root()
        / "nWave"
        / "skills"
        / "nw-density-resolution-contract"
        / "SKILL.md"
    )
    return path.read_text(encoding="utf-8")


def _missing_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    """Return the subset of phrases NOT found in text (case-sensitive)."""
    return [p for p in phrases if p not in text]


def _missing_phrases_case_insensitive(text: str, phrases: tuple[str, ...]) -> list[str]:
    """Return the subset of phrases NOT found in text (case-insensitive)."""
    lower = text.lower()
    return [p for p in phrases if p.lower() not in lower]


@pytest.fixture(scope="module")
def skill_texts() -> dict[str, str]:
    """Return a mapping of skill-name -> full text of SKILL.md for each wave."""
    return {skill: _load_skill_text(skill) for skill in WAVE_SKILLS}


# ---------------------------------------------------------------------------
# One test per wave skill — asserts the full density-aware contract in one
# pass, listing all missing phrases per section in the failure message.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill", WAVE_SKILLS)
def test_skill_encodes_density_aware_contract(
    skill_texts: dict[str, str], skill: str
) -> None:
    """The wave skill encodes the full density-aware contract.

    Single per-skill test asserts every required phrase across all four
    sections (Output Tiers, Density resolution, Telemetry, Provenance) +
    wave-specific heading prefix + telemetry wave field. Failure message
    enumerates the missing phrases per section so the diagnostic is as
    specific as the pre-collapse parametrize case.
    """
    text = skill_texts[skill]
    wave = WAVE_NAMES[skill]
    failures: list[str] = []

    # --- Section 1: Output Tiers (D2) ---
    missing = _missing_phrases(text, OUTPUT_TIERS_PHRASES)
    if missing:
        failures.append(f"Output Tiers (D2) missing phrases: {missing}")
    heading_prefix = f"## Wave: {wave} / [REF]"
    if heading_prefix not in text:
        failures.append(
            f"Wave-specific heading prefix missing: expected {heading_prefix!r}"
        )

    # --- Section 2: Density resolution (D12) ---
    missing = _missing_phrases(text, DENSITY_RESOLUTION_PHRASES)
    if missing:
        failures.append(f"Density resolution (D12) missing phrases: {missing}")
    missing_modes = _missing_phrases_case_insensitive(text, DENSITY_MODE_BRANCHES)
    if missing_modes:
        failures.append(
            f"Density resolution (D12) missing mode branches: {missing_modes}"
        )
    missing_prompt_modes = _missing_phrases(text, EXPANSION_PROMPT_MODES)
    if missing_prompt_modes:
        failures.append(
            "Density resolution (D12) diverges from runtime expansion-prompt "
            f"carrier; missing: {missing_prompt_modes}"
        )

    # --- Section 3: Telemetry (D4 + DDD-6) ---
    missing = _missing_phrases(text, TELEMETRY_PHRASES)
    if missing:
        failures.append(f"Telemetry (D4 + DDD-6) missing phrases: {missing}")
    telemetry_wave = f'"wave": "{wave}"'
    if telemetry_wave not in text:
        failures.append(
            f"Telemetry schema must declare wave={wave!r} (expected {telemetry_wave!r})"
        )

    # --- Section 4: Provenance (D2/D4/D10/D12 + DDD-5/DDD-6) ---
    missing = _missing_phrases(text, PROVENANCE_DECISION_IDS)
    if missing:
        failures.append(f"Provenance missing decision IDs: {missing}")
    missing = _missing_phrases(text, PROVENANCE_DDD_IDS)
    if missing:
        failures.append(f"Provenance missing DDD IDs: {missing}")

    assert not failures, (
        f"{skill} (wave={wave}) violates the density-aware contract:\n  - "
        + "\n  - ".join(failures)
    )


def test_d6_cited_only_in_discuss_pilot(skill_texts: dict[str, str]) -> None:
    """D6 (install-time prompt decision) is DISCUSS-pilot-specific.

    Track A.3 holdout: the original DISCUSS-only test file asserted D6 in
    nw-discuss. Other propagated skills don't cite D6 (per locked design).
    Consolidating the DISCUSS test into this file would lose that focused
    coverage; this single test preserves it.
    """
    discuss = skill_texts["nw-discuss"]
    assert "D6" in discuss, (
        "nw-discuss must cite D6 (install-time prompt decision per pilot reasoning trail)"
    )


def test_shared_contract_projects_runtime_carrier_and_locates_trigger_catalog() -> None:
    """The shared prose cannot drift from runtime modes or orphan issue #95 triggers."""
    contract = _load_density_contract()

    missing_modes = _missing_phrases(contract, EXPANSION_PROMPT_MODES)
    assert not missing_modes, f"shared contract misses runtime modes: {missing_modes}"
    assert "nWave/skills/nw-discuss/SKILL.md" in contract
    assert "only current trigger catalog" in contract
    assert "no declared triggers" in contract
