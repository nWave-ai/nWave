"""Domain types for the roadmap classic-only flagging coherence slice.

slice-11 of the atdd-pure-roadmap-free-rollout (ADR-028 / ADR-029).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed
once here as a typed enum / dataclass / NewType. Step bodies and the
composition service consume these typed parameters -- no raw ``str`` where a
domain enum exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-11's only deliverable is the classic-only / atdd_pure-context prose
added to three production files -- ``nw-roadmap/SKILL.md``, ``nw/roadmap.md``,
``nw-root-why/SKILL.md``. All three are ``.md`` files: NO CLI, NO ``main()``,
NO exit code; ``master`` vs post-slice-11 differ ONLY in markdown text. A
behavioural / regression AT is structurally impossible -- there is nothing to
invoke. Per the **refined H3 rule** (feature-delta L883-893) a slice whose
entire deliverable is ``.md`` prose is Class P, gated by the executable
coherence test (slice-09 / slice-04 / slice-10 / slice-13 precedent). The H3
discriminator (feature-delta L858-859): all three files carry only stale
*description*; no orchestrator reads them to branch.

THE SLICE-11 CONTRACT -- three NEW literal-regex clauses, three files
---------------------------------------------------------------------
slice-11 flags the roadmap skill / command as classic-mode-only and adds an
atdd_pure-context paragraph to nw-root-why. The design note (feature-delta
L843-855, the 3-row regex table) specifies, per file, a single ``present_regex``:

* ``nw-roadmap/SKILL.md``  -- ``classic mode only``
                              (the roadmap skill is flagged classic-only).
* ``nw/roadmap.md``        -- ``not used under .*atdd_pure``
                              (the roadmap command states it is not used under
                              the atdd_pure workflow).
* ``nw-root-why/SKILL.md`` -- ``atdd_pure.*slice.*ledger``
                              (nw-root-why gains an atdd_pure-context paragraph
                              naming the per-slice ledger).

All three rows are ADDITIVE (feature-delta L851-855): a classic-only flag / an
atdd_pure-context paragraph is added; none has a stale literal to delete, so
``absent_regex`` is empty and the gate is the ``present_regex`` match alone.
Every clause is therefore ``ClauseKind.NEW``.

VACUITY AUDIT (acceptance brief requirement)
--------------------------------------------
A NEW literal-regex clause is VACUOUS if its ``present_regex`` already matches
on master (the clause is then already-green = non-falsifiable). Grep evidence
2026-05-20 (``grep -cE <regex> <file>``):

  nw-roadmap/SKILL.md     "classic mode only"          -> 0
  nw/roadmap.md           "not used under .*atdd_pure"  -> 0
  nw-root-why/SKILL.md    "atdd_pure.*slice.*ledger"    -> 0

All three regexes match ZERO times on master -> all three clauses are
NON-VACUOUS. The coherence AT FAILS on master (the regex does not match) and
PASSES once slice-11 adds the prose. No vacuous-clause flag for slice-11.

WHY a SEPARATE test directory
-----------------------------
slices 04 / 15 ship coherence tests over ``nw-deliver/SKILL.md``; slice-09 over
the three finalize-adjacent skills; slice-13 over the three mode/resume/AT-set
skills. slice-11's three files (roadmap skill, roadmap command, root-why skill)
are disjoint from all of those. ``atdd_pure_roadmap_classic_only_coherence``
is the slice-11 scoped directory (underscores, per the directory-naming
mandate).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a production file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class RoadmapFile(str, Enum):
    """The three slice-11 production files under coherence audit.

    Each value is the repo-root-relative path to the real shipped ``.md``
    file. The composition reads the real shipped file (Pillar 3: app as in
    production -- no hand-built fixture copy).
    """

    ROADMAP_SKILL = "nWave/skills/nw-roadmap/SKILL.md"
    ROADMAP_COMMAND = "nWave/tasks/nw/roadmap.md"
    ROOT_WHY_SKILL = "nWave/skills/nw-root-why/SKILL.md"


class ClauseKind(str, Enum):
    """Whether a slice-11 coherence clause is a NEW or a MODE_SCOPED check.

    NEW -- the clause's prose is genuinely added by slice-11. The contract
           carries a ``present_regex`` VERIFIED 0 matches on master; the
           coherence AT FAILS on master and PASSES once slice-11 lands
           (regression-AT contract). All three slice-11 clauses are NEW
           (the design-note table is fully additive: ``absent_regex`` empty
           for every row).

    MODE_SCOPED is retained for shape-parity with the slice-13 precedent but
    is unused by slice-11 -- no slice-11 file has a stale token that
    legitimately remains for the classic path while needing a per-line
    qualifier.
    """

    NEW = "new"


@dataclass(frozen=True)
class CoherenceContract:
    """A single literal-regex coherence assertion over one slice-11 file.

    ``roadmap_file`` -- which of the three slice-11 files this clause governs.
    ``kind``         -- always NEW for slice-11 (the design-note table is
                        fully additive).
    ``present_regex``-- the ``present_regex`` literal from the design-note
                        table (feature-delta L847-849). It MUST match >=1
                        line once slice-11 lands and is VERIFIED 0 matches on
                        master (the regression-AT signal).

    ``__post_init__`` enforces the kind invariant so a malformed contract
    cannot silently re-enter (slice-04 review Blocking 1 / slice-13
    precedent).
    """

    roadmap_file: RoadmapFile
    kind: ClauseKind
    present_regex: str

    def __post_init__(self) -> None:
        if self.kind is not ClauseKind.NEW:
            raise ValueError(
                f"{self.roadmap_file.value}: slice-11 clauses are all NEW "
                f"(the design-note table is fully additive); got "
                f"{self.kind.value}"
            )
        if not self.present_regex:
            raise ValueError(
                f"{self.roadmap_file.value}: a NEW clause must declare a "
                f"non-empty present_regex (its regression-AT signal)"
            )


# The slice-11 coherence contracts. The composition service
# (RoadmapClassicOnlyComposition) evaluates each against its target file.
#
# present_regex literals copied verbatim from the design-note 3-row table
# (feature-delta L847-849). Every regex verified 0 matches on master
# 2026-05-20 (see the module docstring VACUITY AUDIT) -- all NON-VACUOUS.

COHERENCE_CONTRACTS: dict[RoadmapFile, CoherenceContract] = {
    # nw-roadmap/SKILL.md -- the roadmap skill is flagged classic-mode-only.
    RoadmapFile.ROADMAP_SKILL: CoherenceContract(
        roadmap_file=RoadmapFile.ROADMAP_SKILL,
        kind=ClauseKind.NEW,
        present_regex=r"classic mode only",
    ),
    # nw/roadmap.md -- the roadmap command states it is not used under the
    # atdd_pure workflow.
    RoadmapFile.ROADMAP_COMMAND: CoherenceContract(
        roadmap_file=RoadmapFile.ROADMAP_COMMAND,
        kind=ClauseKind.NEW,
        present_regex=r"not used under .*atdd_pure",
    ),
    # nw-root-why/SKILL.md -- gains an atdd_pure-context paragraph naming the
    # per-slice ledger.
    RoadmapFile.ROOT_WHY_SKILL: CoherenceContract(
        roadmap_file=RoadmapFile.ROOT_WHY_SKILL,
        kind=ClauseKind.NEW,
        present_regex=r"atdd_pure.*slice.*ledger",
    ),
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

ROADMAP_FILE_BY_PHRASE: dict[str, RoadmapFile] = {
    "the nw-roadmap skill": RoadmapFile.ROADMAP_SKILL,
    "the nw-roadmap command": RoadmapFile.ROADMAP_COMMAND,
    "the nw-root-why skill": RoadmapFile.ROOT_WHY_SKILL,
}
