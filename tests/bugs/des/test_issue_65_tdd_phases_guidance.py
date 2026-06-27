"""RED guard (issue #65, downstream): the TDD_PHASES recovery guidance must name
the ADR-025 3-phase canon (RED/GREEN/COMMIT), not instruct the user to list the
legacy 5 phases.

``MandatorySectionChecker.RECOVERY_GUIDANCE_MAP["TDD_PHASES"]``
(``src/des/application/validator.py``) currently reads
"...listing all 5 phases: PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT" —
stale post-ADR-025 guidance that tells a user to re-introduce the very legacy
phases the canon dropped. That is the same v4-vs-v5 drift class issue #65 fixed
in the gate, surviving in the user-facing recovery text.

These assertions are the GREEN contract; the guidance fix itself was a doc-only
string change (no production logic). They were authored as ``xfail(strict=True)``
RED guards and flipped to normal passing tests once the guidance string was
corrected to the 3-phase canon — the marker, and the stale string, removed
together.

Robust to wording: a *standalone* ``RED`` token plus GREEN and COMMIT, and the
absence of the legacy-only names — not an exact-string match. The standalone
check matters because the legacy string contains ``RED`` only as a substring of
``RED_ACCEPTANCE`` / ``RED_UNIT``; a naive ``"RED" in guidance`` would be
satisfied coincidentally and give a false GREEN.

Refs: https://github.com/nWave-ai/nWave/issues/65 ; ADR-025 (2026-05-07).
"""

from __future__ import annotations

import re

from des.application.validator import MandatorySectionChecker


LEGACY_ONLY = ("PREPARE", "RED_ACCEPTANCE", "RED_UNIT")


def _tdd_phases_guidance() -> str:
    return MandatorySectionChecker.RECOVERY_GUIDANCE_MAP["TDD_PHASES"]


def test_guidance_names_the_three_phase_canon() -> None:
    """Guidance should name the canonical phases: a standalone RED token (not
    only RED_ACCEPTANCE / RED_UNIT), plus GREEN and COMMIT."""
    guidance = _tdd_phases_guidance()
    has_standalone_red = re.search(r"\bRED\b", guidance) is not None
    missing = []
    if not has_standalone_red:
        missing.append("RED")
    missing += [phase for phase in ("GREEN", "COMMIT") if phase not in guidance]
    assert not missing, (
        f"TDD_PHASES recovery guidance omits canonical phases {missing}; "
        f"guidance={guidance!r}"
    )


def test_guidance_does_not_instruct_listing_legacy_only_phases() -> None:
    """Guidance should not tell the user to list PREPARE/RED_ACCEPTANCE/RED_UNIT."""
    guidance = _tdd_phases_guidance()
    leaked = [phase for phase in LEGACY_ONLY if phase in guidance]
    assert not leaked, (
        "TDD_PHASES recovery guidance still tells the user to list legacy-only "
        f"phases {leaked} dropped by ADR-025; guidance={guidance!r}"
    )
