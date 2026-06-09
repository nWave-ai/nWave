r"""Domain types for the review-methodology + reviewer-agent coherence slice.

slice-10 of the atdd-pure-roadmap-free-rollout (ADR-028 7-phase A->G sibling
spine + ADR-029 PO/ATD reviewer DoR/DoD re-split).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed once
here as a typed enum / dataclass / NewType. Step bodies and the composition
service consume these typed parameters -- no raw ``str`` where a domain enum
exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-10's only deliverable is the atdd_pure-coherence prose edited into six
review-methodology / reviewer-agent files -- three skill ``SKILL.md`` files and
three reviewer ``.md`` agent specs. All six are prose: NO CLI, NO ``main()``,
NO exit code; ``master`` vs post-slice-10 differ ONLY in markdown text. A
behavioural / regression AT is structurally impossible -- there is nothing to
invoke. Per the refined H3 rule (feature-delta ``[REF] Slice classes``) a slice
whose entire deliverable is ``.md`` prose is Class P, gated by the executable
coherence test (slice-04 / slice-09 / slice-15 precedent).

THE SLICE-10 CONTRACT -- two coherence mechanisms, six files
------------------------------------------------------------
The slice-10 design note (feature-delta L751-835) fixes the gate as
"100% mechanical, two mechanisms":

* REGEX coherence check -- 4 files. Each carries a bare-token contract: an
  ``absent_regex`` that MUST match zero lines after the slice and a
  ``present_regex`` that MUST match >=1 line after the slice. POSIX ERE,
  case-sensitive.

    | File                          | absent_regex                       | present_regex               |
    |-------------------------------|-------------------------------------|-----------------------------|
    | nw-review/SKILL.md            | extension of ADR-025                | roadmap-free sibling spine  |
    | nw-deliver-orchestration/...  | 7-phase extension                   | roadmap-free sibling spine  |
    | nw-product-owner-reviewer.md  | AC derived from UAT                 | slice plan passes           |
    | nw-acceptance-designer-rev... | derived from PO Given-When-Then     | ATs ARE the acceptance crit |

* SEMANTIC-ROLE executable coherence test -- 2 files (nw-tdd-review-enforcement,
  nw-software-crafter-reviewer). The forbidden item is the *semantic role*
  "``execution-log.json`` is THE / the sole phase record". A bare absent_regex
  on ``execution-log\.json`` is wrong -- it would also forbid the legitimate
  classic-mode reference. The contract is a falsifiable positive predicate:
    - Predicate 1: the file NAMES the atdd_pure phase record -- "AT-completion
      ledger" (a master-absent token).
    - Predicate 2: every line mentioning ``execution-log.json`` co-occurs with
      a ``classic`` / ``workflow.mode`` qualifier on the SAME line.

VACUITY AUDIT -- 2026-05-20 (acceptance brief requirement)
----------------------------------------------------------
Per the slice-10 task spec, every clause already satisfied on master is
non-falsifiable and must be flagged. Grep evidence against current master:

  REGEX files -- absent_regex tokens (master occurrence count):
    nw-review/SKILL.md            "extension of ADR-025"            -> 0  *
    nw-deliver-orchestration/...  "7-phase extension"               -> 0  *
    nw-product-owner-reviewer.md  "AC derived from UAT"             -> 0  *
    nw-acceptance-designer-rev... "derived from PO Given-When-Then" -> 0  *
  REGEX files -- present_regex tokens (master occurrence count):
    nw-review/SKILL.md            "roadmap-free sibling spine"      -> 0
    nw-deliver-orchestration/...  "roadmap-free sibling spine"      -> 0
    nw-product-owner-reviewer.md  "slice plan passes"               -> 0
    nw-acceptance-designer-rev... "ATs ARE the acceptance criteria" -> 0

  (*) VACUITY FLAG. All four ``absent_regex`` patterns ALREADY match zero
  lines on master. The design-note gate semantics ("absent_regex MUST match
  zero AFTER the slice") are still satisfied -- but the absent clause is
  NON-FALSIFIABLE: it cannot distinguish master from post-slice-10. There is
  no stale literal to delete in any of the four files. Per the task's vacuity
  rule these absent clauses are flagged, NOT shipped as standalone assertions.

  HOW slice-10's regex contract is kept HONEST despite the vacuous absent
  clauses: the ``present_regex`` token of every regex row is verified 0
  occurrences on master -- so the PRESENT predicate is genuinely falsifiable
  (FAILS on master, PASSES once slice-10 adds the prose). The coherence test
  therefore asserts the PRESENT predicate as the regression signal, and
  asserts the ABSENT predicate only as a guard that the absent token stays
  zero (which it already is) -- the absent guard is documented as a
  non-regression invariant, not a slice-10 RED signal. The regression RED for
  every regex file comes exclusively from the falsifiable PRESENT predicate.

  SEMANTIC-ROLE files -- 2026-05-20 grep evidence:
    nw-tdd-review-enforcement/SKILL.md  "AT-completion ledger"     -> 0
    nw-tdd-review-enforcement/SKILL.md  "execution-log.json" lines -> 3,
        ALL unscoped (no classic / workflow.mode qualifier): L93, L95, L260.
    nw-software-crafter-reviewer.md     "AT-completion ledger"     -> 0
    nw-software-crafter-reviewer.md     "execution-log.json" lines -> 3,
        ALL unscoped: L80, L86, L171.
  Both semantic-role files are NON-VACUOUS for BOTH predicates: predicate 1
  fails (the ledger token is absent on master), predicate 2 fails (each file
  has >=1 unscoped execution-log.json line). No vacuity flag for the two
  semantic-role files.

WHY a SEPARATE test directory
-----------------------------
slices 04 / 09 / 15 ship coherence tests over disjoint file sets. slice-10's
six files (three review skills + three reviewer agents) are disjoint from
those. ``atdd_pure_review_methodology_coherence`` is the slice-10-scoped
directory (underscores, per the directory-naming mandate).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class CoherenceFile(str, Enum):
    """The six slice-10 review-methodology / reviewer-agent files.

    Each value is the repo-root-relative path to the production file. The
    composition reads the real shipped file (Pillar 3: app as in production --
    no hand-built fixture copy).

    The first four are gated by the REGEX mechanism, the last two by the
    SEMANTIC-ROLE mechanism (slice-10 design note H2-final).
    """

    NW_REVIEW = "nWave/skills/nw-review/SKILL.md"
    NW_DELIVER_ORCHESTRATION = "nWave/skills/nw-deliver-orchestration/SKILL.md"
    NW_PRODUCT_OWNER_REVIEWER = "nWave/agents/nw-product-owner-reviewer.md"
    NW_ACCEPTANCE_DESIGNER_REVIEWER = "nWave/agents/nw-acceptance-designer-reviewer.md"
    NW_TDD_REVIEW_ENFORCEMENT = "nWave/skills/nw-tdd-review-enforcement/SKILL.md"
    NW_SOFTWARE_CRAFTER_REVIEWER = "nWave/agents/nw-software-crafter-reviewer.md"


class Mechanism(str, Enum):
    """Which of the two slice-10 coherence mechanisms gates a file.

    REGEX         -- a bare-token contract: an ``absent_regex`` (zero lines
                     after the slice) plus a ``present_regex`` (>=1 line after
                     the slice). The PRESENT token is the falsifiable
                     regression signal.
    SEMANTIC_ROLE -- a falsifiable positive predicate over the semantic role
                     "execution-log.json is THE phase record": the file must
                     NAME the atdd_pure phase record and every
                     execution-log.json line must be classic-scoped.
    """

    REGEX = "regex"
    SEMANTIC_ROLE = "semantic_role"


@dataclass(frozen=True)
class RegexContract:
    """A REGEX-mechanism coherence contract over one slice-10 file.

    ``coherence_file``  -- which of the four REGEX-gated files this governs.
    ``absent_regex``    -- a POSIX-ERE pattern that MUST match zero lines after
                           the slice. Per the slice-10 vacuity audit all four
                           absent patterns ALREADY match zero on master -- the
                           absent clause is a non-regression GUARD, not the
                           slice-10 RED signal.
    ``present_regex``   -- a POSIX-ERE pattern that MUST match >=1 line after
                           the slice. VERIFIED 0 occurrences on master
                           2026-05-20 -- this is the falsifiable regression
                           signal (FAILS on master, PASSES after slice-10).
    ``absent_is_vacuous``
                        -- True iff ``absent_regex`` already matches zero on
                           master. When True the test still runs the absent
                           guard but documents it as non-falsifiable; the RED
                           signal is the present predicate alone.

    ``__post_init__`` enforces that an absent / present regex is non-empty so a
    malformed contract cannot silently re-enter (slice-04 review Blocking 1
    precedent).
    """

    coherence_file: CoherenceFile
    absent_regex: str
    present_regex: str
    absent_is_vacuous: bool

    def __post_init__(self) -> None:
        if not self.absent_regex:
            raise ValueError(
                f"{self.coherence_file.value}: a REGEX contract must declare a "
                f"non-empty absent_regex"
            )
        if not self.present_regex:
            raise ValueError(
                f"{self.coherence_file.value}: a REGEX contract must declare a "
                f"non-empty present_regex"
            )


@dataclass(frozen=True)
class SemanticRoleContract:
    """A SEMANTIC-ROLE-mechanism coherence contract over one slice-10 file.

    ``coherence_file``      -- one of the two SEMANTIC-ROLE-gated files
                               (nw-tdd-review-enforcement, nw-software-crafter-
                               reviewer).
    ``ledger_token``        -- the master-absent token that NAMES the atdd_pure
                               phase record. VERIFIED 0 occurrences on master
                               2026-05-20 -- predicate 1's falsifiable signal.
    ``phase_record_tokens`` -- the classic-mode phase-record tokens whose every
                               occurrence line must carry a qualifier.
    ``qualifier_tokens``    -- the qualifier tokens, at least one of which must
                               co-occur on a phase-record line.

    ``__post_init__`` enforces every field is non-empty.
    """

    coherence_file: CoherenceFile
    ledger_token: str
    phase_record_tokens: tuple[str, ...]
    qualifier_tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.ledger_token:
            raise ValueError(
                f"{self.coherence_file.value}: a SEMANTIC-ROLE contract must "
                f"declare a ledger_token (predicate 1's falsifiable signal)"
            )
        if not self.phase_record_tokens:
            raise ValueError(
                f"{self.coherence_file.value}: a SEMANTIC-ROLE contract must "
                f"declare phase_record_tokens (the lines it scopes)"
            )
        if not self.qualifier_tokens:
            raise ValueError(
                f"{self.coherence_file.value}: a SEMANTIC-ROLE contract must "
                f"declare qualifier_tokens (the classic / workflow.mode "
                f"qualifiers)"
            )


# The qualifier tokens that scope a phase-record line to the classic path.
# Either one on the line satisfies the mode-scope predicate (slice-10 design
# note executable-coherence-test predicate 2: ``\bclassic\b|workflow\.mode``).
_QUALIFIERS: tuple[str, ...] = ("classic", "workflow.mode")

# The classic-mode phase-record token whose every occurrence line must be
# classic-scoped after slice-10.
_PHASE_RECORD_TOKENS: tuple[str, ...] = ("execution-log.json",)


# --- REGEX contracts (4 files) -----------------------------------------------
#
# Every present_regex string was verified 0 occurrences on master 2026-05-20
# (the falsifiable regression signal). Every absent_regex string was ALSO
# verified 0 occurrences on master -- the absent clause is therefore
# non-falsifiable (``absent_is_vacuous=True``) and the test documents it as a
# non-regression guard, NOT a slice-10 RED signal.

REGEX_CONTRACTS: dict[CoherenceFile, RegexContract] = {
    CoherenceFile.NW_REVIEW: RegexContract(
        coherence_file=CoherenceFile.NW_REVIEW,
        absent_regex=r"extension of ADR-025",
        present_regex=r"roadmap-free sibling spine",
        absent_is_vacuous=True,
    ),
    CoherenceFile.NW_DELIVER_ORCHESTRATION: RegexContract(
        coherence_file=CoherenceFile.NW_DELIVER_ORCHESTRATION,
        absent_regex=r"7-phase extension",
        present_regex=r"roadmap-free sibling spine",
        absent_is_vacuous=True,
    ),
    CoherenceFile.NW_PRODUCT_OWNER_REVIEWER: RegexContract(
        coherence_file=CoherenceFile.NW_PRODUCT_OWNER_REVIEWER,
        absent_regex=r"AC derived from UAT",
        present_regex=r"slice plan passes",
        absent_is_vacuous=True,
    ),
    CoherenceFile.NW_ACCEPTANCE_DESIGNER_REVIEWER: RegexContract(
        coherence_file=CoherenceFile.NW_ACCEPTANCE_DESIGNER_REVIEWER,
        absent_regex=r"derived from PO Given-When-Then",
        present_regex=r"ATs ARE the acceptance criteria",
        absent_is_vacuous=True,
    ),
}


# --- SEMANTIC-ROLE contracts (2 files) ---------------------------------------
#
# ledger_token "AT-completion ledger" verified 0 occurrences on master in both
# files 2026-05-20. Each file carries 3 unscoped execution-log.json lines on
# master -- predicate 2 is non-vacuous for both.

SEMANTIC_ROLE_CONTRACTS: dict[CoherenceFile, SemanticRoleContract] = {
    CoherenceFile.NW_TDD_REVIEW_ENFORCEMENT: SemanticRoleContract(
        coherence_file=CoherenceFile.NW_TDD_REVIEW_ENFORCEMENT,
        ledger_token="AT-completion ledger",
        phase_record_tokens=_PHASE_RECORD_TOKENS,
        qualifier_tokens=_QUALIFIERS,
    ),
    CoherenceFile.NW_SOFTWARE_CRAFTER_REVIEWER: SemanticRoleContract(
        coherence_file=CoherenceFile.NW_SOFTWARE_CRAFTER_REVIEWER,
        ledger_token="AT-completion ledger",
        phase_record_tokens=_PHASE_RECORD_TOKENS,
        qualifier_tokens=_QUALIFIERS,
    ),
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

REGEX_FILE_BY_PHRASE: dict[str, CoherenceFile] = {
    "the nw-review skill": CoherenceFile.NW_REVIEW,
    "the nw-deliver-orchestration skill": CoherenceFile.NW_DELIVER_ORCHESTRATION,
    "the product-owner reviewer agent": CoherenceFile.NW_PRODUCT_OWNER_REVIEWER,
    "the acceptance-designer reviewer agent": (
        CoherenceFile.NW_ACCEPTANCE_DESIGNER_REVIEWER
    ),
}

SEMANTIC_ROLE_FILE_BY_PHRASE: dict[str, CoherenceFile] = {
    "the tdd-review-enforcement skill": CoherenceFile.NW_TDD_REVIEW_ENFORCEMENT,
    "the software-crafter reviewer agent": CoherenceFile.NW_SOFTWARE_CRAFTER_REVIEWER,
}
