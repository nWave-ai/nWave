"""Domain types for the documentation coherence slice.

slice-12 of the atdd-pure-roadmap-free-rollout (ADR-028 / ADR-029).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed
once here as a typed enum / dataclass / NewType. Step bodies and the
composition service consume these typed parameters -- no raw ``str`` where a
domain enum exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-12's only deliverable is the atdd_pure documentation prose added to
three documentation files -- ``docs/reference/des-markers.md``,
``docs/guides/tutorial-deliver-feature/README.md``,
``docs/analysis/wave-flow-precise-map.md``. All three are ``.md`` doc files:
NO CLI, NO ``main()``, NO exit code; ``master`` vs post-slice-12 differ ONLY
in markdown text. A behavioural / regression AT is structurally impossible --
there is nothing to invoke. Per the **refined H3 rule** (feature-delta
L883-893) a slice whose entire deliverable is ``.md`` prose is Class P, gated
by the executable coherence test (slice-09 / slice-04 / slice-10 / slice-13
precedent). H3 discriminator (feature-delta L878-880): pure documentation,
unambiguously no runtime read.

THE SLICE-12 CONTRACT -- three NEW literal-regex clauses, three files
---------------------------------------------------------------------
slice-12 documents the atdd_pure path alongside the retained classic path.
The design note (feature-delta L866-876, the 3-row regex table) specifies, per
file, a single ``present_regex``:

* ``des-markers.md``                       -- ``AT-completion ledger``
                                              (the marker reference names the
                                              AT-completion ledger artifact).
* ``tutorial-deliver-feature/README.md``   -- ``atdd_pure``
                                              (the deliver tutorial names the
                                              atdd_pure workflow).
* ``wave-flow-precise-map.md``             -- ``carpaccio``
                                              (the wave-flow map names the
                                              carpaccio slicing model).

All three rows are ADDITIVE (feature-delta L874-876): the atdd_pure path is
documented *alongside* the retained classic path -- nothing is deleted, so
``absent_regex`` is empty and the gate is the ``present_regex`` match alone.
Every clause is therefore ``ClauseKind.NEW``.

Note: ``wave-flow-precise-map.md`` is under ``docs/analysis/`` (internal,
public-sync-excluded) -- still in scope, it must not mislead internal readers
(feature-delta L880-881).

VACUITY AUDIT (acceptance brief requirement)
--------------------------------------------
A NEW literal-regex clause is VACUOUS if its ``present_regex`` already matches
on master (the clause is then already-green = non-falsifiable). Grep evidence
2026-05-20 (``grep -cE <regex> <file>``):

  des-markers.md                       "AT-completion ledger" -> 0
  tutorial-deliver-feature/README.md   "atdd_pure"            -> 0
  wave-flow-precise-map.md             "carpaccio"            -> 0

All three regexes match ZERO times on master -> all three clauses are
NON-VACUOUS. The coherence AT FAILS on master (the regex does not match) and
PASSES once slice-12 adds the prose. No vacuous-clause flag for slice-12.

WHY a SEPARATE test directory
-----------------------------
slices 04 / 15 ship coherence tests over ``nw-deliver/SKILL.md``; slice-09
over the three finalize-adjacent skills; slice-11 over the roadmap skill /
command / root-why skill; slice-13 over the three mode/resume/AT-set skills.
slice-12's three files (a reference doc, a tutorial, an analysis doc) are
disjoint from all of those. ``atdd_pure_documentation_coherence`` is the
slice-12 scoped directory (underscores, per the directory-naming mandate).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a documentation file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class DocFile(str, Enum):
    """The three slice-12 documentation files under coherence audit.

    Each value is the repo-root-relative path to the real shipped ``.md``
    file. The composition reads the real shipped file (Pillar 3: app as in
    production -- no hand-built fixture copy).
    """

    DES_MARKERS = "docs/reference/des-markers.md"
    DELIVER_TUTORIAL = "docs/guides/tutorial-deliver-feature/README.md"
    WAVE_FLOW_MAP = "docs/analysis/wave-flow-precise-map.md"


class ClauseKind(str, Enum):
    """Whether a slice-12 coherence clause is a NEW or a MODE_SCOPED check.

    NEW -- the clause's prose is genuinely added by slice-12. The contract
           carries a ``present_regex`` VERIFIED 0 matches on master; the
           coherence AT FAILS on master and PASSES once slice-12 lands
           (regression-AT contract). All three slice-12 clauses are NEW
           (the design-note table is fully additive: ``absent_regex`` empty
           for every row).

    MODE_SCOPED is retained for shape-parity with the slice-13 precedent but
    is unused by slice-12 -- no slice-12 file has a stale token that
    legitimately remains for the classic path while needing a per-line
    qualifier.
    """

    NEW = "new"


@dataclass(frozen=True)
class CoherenceContract:
    """A single literal-regex coherence assertion over one slice-12 doc file.

    ``doc_file``     -- which of the three slice-12 files this clause governs.
    ``kind``         -- always NEW for slice-12 (the design-note table is
                        fully additive).
    ``present_regex``-- the ``present_regex`` literal from the design-note
                        table (feature-delta L870-872). It MUST match >=1
                        line once slice-12 lands and is VERIFIED 0 matches on
                        master (the regression-AT signal).

    ``__post_init__`` enforces the kind invariant so a malformed contract
    cannot silently re-enter (slice-04 review Blocking 1 / slice-13
    precedent).
    """

    doc_file: DocFile
    kind: ClauseKind
    present_regex: str

    def __post_init__(self) -> None:
        if self.kind is not ClauseKind.NEW:
            raise ValueError(
                f"{self.doc_file.value}: slice-12 clauses are all NEW "
                f"(the design-note table is fully additive); got "
                f"{self.kind.value}"
            )
        if not self.present_regex:
            raise ValueError(
                f"{self.doc_file.value}: a NEW clause must declare a "
                f"non-empty present_regex (its regression-AT signal)"
            )


# The slice-12 coherence contracts. The composition service
# (DocumentationCoherenceComposition) evaluates each against its target file.
#
# present_regex literals copied verbatim from the design-note 3-row table
# (feature-delta L870-872). Every regex verified 0 matches on master
# 2026-05-20 (see the module docstring VACUITY AUDIT) -- all NON-VACUOUS.

COHERENCE_CONTRACTS: dict[DocFile, CoherenceContract] = {
    # docs/reference/des-markers.md -- the marker reference names the
    # AT-completion ledger artifact.
    DocFile.DES_MARKERS: CoherenceContract(
        doc_file=DocFile.DES_MARKERS,
        kind=ClauseKind.NEW,
        present_regex=r"AT-completion ledger",
    ),
    # docs/guides/tutorial-deliver-feature/README.md -- the deliver tutorial
    # names the atdd_pure workflow.
    DocFile.DELIVER_TUTORIAL: CoherenceContract(
        doc_file=DocFile.DELIVER_TUTORIAL,
        kind=ClauseKind.NEW,
        present_regex=r"atdd_pure",
    ),
    # docs/analysis/wave-flow-precise-map.md -- the wave-flow map names the
    # carpaccio slicing model.
    DocFile.WAVE_FLOW_MAP: CoherenceContract(
        doc_file=DocFile.WAVE_FLOW_MAP,
        kind=ClauseKind.NEW,
        present_regex=r"carpaccio",
    ),
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

DOC_FILE_BY_PHRASE: dict[str, DocFile] = {
    "the des-markers reference": DocFile.DES_MARKERS,
    "the deliver-feature tutorial": DocFile.DELIVER_TUTORIAL,
    "the wave-flow precise map": DocFile.WAVE_FLOW_MAP,
}
