"""Domain types for the mode-detection / resume / AT-set-audit coherence slice.

slice-13 of the atdd-pure-roadmap-free-rollout (ADR-028 / ADR-029).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed
once here as a typed enum / dataclass / NewType. Step bodies and the
composition service consume these typed parameters -- no raw ``str`` where a
domain enum exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-13's only deliverable is the atdd_pure prose added to three skill files
-- ``nw-fast-forward``, ``nw-buddy-project-reading``, ``nw-at-completeness-check``.
All three are skill ``SKILL.md`` *prose* files: NO CLI, NO ``main()``, NO exit
code; ``master`` vs post-slice-13 differ ONLY in markdown text. A behavioural /
regression AT is structurally impossible -- there is nothing to invoke. Per the
**refined H3 rule** (feature-delta L883-893) a slice whose entire deliverable is
``.md`` prose is Class P, gated by the executable coherence test (slice-09 /
slice-04 / slice-10 / slice-15 precedent). The H3 re-typing rationale: the data
artifacts these skills DESCRIBE reading -- the AT-completion ledger,
``.nwave/config.yaml:workflow.mode``, the per-slice AT set -- are created by the
CLIs of slices 01-03, NOT by these skill files.

THE SLICE-13 CONTRACT -- two clause families, three files
---------------------------------------------------------
slice-13 aligns the three skills with the ATDD-pure roadmap-free spine. The
design note (feature-delta L897-902) specifies, per file:

* ``nw-fast-forward``        -- describe computing the resume position from the
                                AT-completion ledger phase-boundary records
                                (NOT ``execution-log.json``).
* ``nw-buddy-project-reading``- describe detecting project mode from
                                ``.nwave/config.yaml:workflow.mode`` (NOT the
                                presence of ``roadmap.json``).
* ``nw-at-completeness-check``- describe auditing the per-slice AT set (NOT an
                                all-ATs-up-front contract).

Two clause families:

* NEW clauses (``ClauseKind.NEW``) -- each file must NAME the atdd_pure path.
  Each NEW clause carries a ``master_absent_substring`` VERIFIED 0 occurrences
  on master 2026-05-20 (grep evidence table in the acceptance brief). The
  coherence AT FAILS on master and PASSES once slice-13 lands.

* MODE_SCOPED clauses (``ClauseKind.MODE_SCOPED``) -- the slice-09 / slice-10
  semantic-role pattern. NOT a bare-token absence (``roadmap.json`` /
  ``execution-log`` legitimately remain for the CLASSIC path); the falsifiable
  positive predicate is "every line mentioning the scope token co-occurs with a
  ``classic`` / ``workflow.mode`` qualifier on the SAME line".

VACUITY AUDIT (acceptance brief requirement -- read the brief discrepancy flags)
--------------------------------------------------------------------------------
A MODE_SCOPED clause is VACUOUS if the scope token is already absent / already
fully scoped on master (the per-line check then has nothing to falsify). An
ABSENCE clause is VACUOUS if the forbidden token is already absent on master.

Grep evidence 2026-05-20 (`grep -cF <token> nWave/skills/<file>/SKILL.md`):

  nw-fast-forward/SKILL.md
    "roadmap.json"            -> 0    "execution-log"        -> 0
    "atdd_pure"               -> 0    "AT-completion ledger" -> 0
    "workflow.mode"           -> 0
  nw-buddy-project-reading/SKILL.md
    "roadmap.json"            -> 1 (L92, UNSCOPED)
    "execution-log"           -> 0
    "atdd_pure"               -> 0    "workflow.mode"        -> 0
    "AT-completion ledger"    -> 0
  nw-at-completeness-check/SKILL.md
    "execution-log"           -> 0    "roadmap.json"         -> 0
    "all ATs up front"        -> 0    "up front"             -> 0
    "per-slice"               -> 0    "atdd_pure"            -> 0
    "AT-completion ledger"    -> 0

CONSEQUENCES -- two design-note clauses are VACUOUS and are NOT shipped:

  (1) The design note's MODE-SCOPED requirement for ``nw-fast-forward``
      ("every roadmap.json / execution-log mention co-occurs with a classic /
      workflow.mode qualifier") is VACUOUS -- master has 0 ``roadmap.json`` and
      0 ``execution-log`` lines in nw-fast-forward. A per-line scoping check
      over zero lines passes trivially on master AND post-slice-13 -> it is not
      a regression signal. nw-fast-forward gets a NEW clause ONLY. The honest
      contract is "the resume prose NAMES the AT-completion ledger" (a
      master-absent token), not "every log mention is scoped" (no log mention
      exists to scope).

  (2) The design note's ABSENCE requirement for ``nw-at-completeness-check``
      ("the stale 'all ATs up front' framing as unconditional" must be absent)
      is VACUOUS -- master has 0 occurrences of "all ATs up front" / "up front".
      An ABSENCE clause needs the forbidden token PRESENT on master to be
      non-vacuous. nw-at-completeness-check gets a NEW clause ONLY. The honest
      contract is "the skill NAMES auditing the per-slice AT set" (a
      master-absent token).

NON-VACUOUS clause that IS shipped:

  (3) The MODE-SCOPED clause for ``nw-buddy-project-reading`` IS non-vacuous --
      master L92 ("`docs/feature/{id}/deliver/roadmap.json`") is an UNSCOPED
      ``roadmap.json`` mention. After slice-13 every ``roadmap.json`` line must
      co-occur with a ``classic`` / ``workflow.mode`` qualifier (the classic
      DELIVER path keeps roadmap.json; the atdd_pure path uses
      ``workflow.mode``). The per-line check genuinely FAILS on master.

WHY a SEPARATE test directory
-----------------------------
slices 04 / 15 ship coherence tests over ``nw-deliver/SKILL.md``; slice-09 over
the three finalize-adjacent skills; slice-13's three files are disjoint from
all of those. ``atdd_pure_mode_detection_resume_coherence`` is the slice-13
scoped directory (underscores, per the directory-naming mandate).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a skill file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class SkillFile(str, Enum):
    """The three slice-13 skill files under coherence audit.

    Each value is the repo-root-relative path to the production ``SKILL.md``.
    The composition reads the real shipped file (Pillar 3: app as in
    production -- no hand-built fixture copy).
    """

    FAST_FORWARD = "nWave/skills/nw-fast-forward/SKILL.md"
    BUDDY_PROJECT_READING = "nWave/skills/nw-buddy-project-reading/SKILL.md"
    AT_COMPLETENESS_CHECK = "nWave/skills/nw-at-completeness-check/SKILL.md"


class ClauseKind(str, Enum):
    """Whether a slice-13 coherence clause is a NEW-prose or a MODE_SCOPED check.

    NEW         -- the clause's prose is genuinely added by slice-13. The
                   contract carries a ``master_absent_substring`` VERIFIED
                   absent on master; the coherence AT FAILS on master and
                   PASSES once slice-13 lands (regression-AT contract).
    MODE_SCOPED -- the clause is a semantic-role predicate (slice-09 / slice-10
                   pattern): every line mentioning a scope token must co-occur
                   with a ``classic`` / ``workflow.mode`` qualifier. It carries
                   NO ``master_absent_substring`` (the token is legitimately
                   present for the classic path); its regression signal is the
                   per-line scoping check, which is NON-VACUOUS only when
                   master has >=1 unscoped line.
    """

    NEW = "new"
    MODE_SCOPED = "mode_scoped"


@dataclass(frozen=True)
class CoherenceContract:
    """A single coherence assertion over one slice-13 skill file.

    ``skill``       -- which of the three slice-13 files this clause governs.
    ``kind``        -- NEW or MODE_SCOPED.
    ``present_substrings``
                    -- domain tokens that MUST all appear in the file once
                       slice-13 lands. For a NEW clause these are the new
                       atdd_pure prose tokens; for a MODE_SCOPED clause this
                       is empty (a mode-scoped clause asserts a per-line
                       property, not bare presence).
    ``master_absent_substring``
                    -- for a NEW clause, one token VERIFIED 0 occurrences on
                       master, proving the clause is genuinely new (the AT
                       FAILS on master, PASSES after slice-13). REQUIRED for
                       NEW, MUST be ``None`` for MODE_SCOPED.
    ``scope_tokens``-- for a MODE_SCOPED clause, the tokens whose every
                       occurrence line must carry a qualifier. MUST be
                       non-empty for MODE_SCOPED, MUST be empty for NEW.
    ``qualifier_tokens``
                    -- for a MODE_SCOPED clause, the qualifier tokens at least
                       one of which must co-occur on a scope-token line. MUST
                       be non-empty for MODE_SCOPED, MUST be empty for NEW.

    ``__post_init__`` enforces the kind invariants so a false-absent or a
    malformed mode-scoped contract cannot silently re-enter (slice-04 review
    Blocking 1 / slice-09 precedent).
    """

    skill: SkillFile
    kind: ClauseKind
    present_substrings: tuple[str, ...]
    master_absent_substring: str | None
    scope_tokens: tuple[str, ...]
    qualifier_tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind is ClauseKind.NEW:
            if self.master_absent_substring is None:
                raise ValueError(
                    f"{self.skill.value}: a NEW clause must declare a "
                    f"master_absent_substring (its regression-AT signal)"
                )
            if not self.present_substrings:
                raise ValueError(
                    f"{self.skill.value}: a NEW clause must declare present_substrings"
                )
            if self.scope_tokens or self.qualifier_tokens:
                raise ValueError(
                    f"{self.skill.value}: a NEW clause must NOT declare "
                    f"scope_tokens / qualifier_tokens (it is not a per-line "
                    f"mode-scope check)"
                )
            if self.master_absent_substring not in self.present_substrings:
                raise ValueError(
                    f"{self.skill.value}: the master_absent_substring "
                    f"'{self.master_absent_substring}' must also be one of the "
                    f"present_substrings (the slice-13 prose adds it)"
                )
        if self.kind is ClauseKind.MODE_SCOPED:
            if self.master_absent_substring is not None:
                raise ValueError(
                    f"{self.skill.value}: a MODE_SCOPED clause must NOT declare "
                    f"a master_absent_substring (the token is legitimately "
                    f"present for the classic path)"
                )
            if self.present_substrings:
                raise ValueError(
                    f"{self.skill.value}: a MODE_SCOPED clause must NOT declare "
                    f"present_substrings (it asserts a per-line property)"
                )
            if not self.scope_tokens:
                raise ValueError(
                    f"{self.skill.value}: a MODE_SCOPED clause must declare "
                    f"scope_tokens (the lines it scopes)"
                )
            if not self.qualifier_tokens:
                raise ValueError(
                    f"{self.skill.value}: a MODE_SCOPED clause must declare "
                    f"qualifier_tokens (the classic / workflow.mode qualifiers)"
                )


# The two qualifier tokens that scope a roadmap-classic line to the classic
# path. Either one on the line satisfies the mode-scope predicate.
_QUALIFIERS: tuple[str, ...] = ("classic", "workflow.mode")


# The slice-13 coherence contracts. The composition service
# (ModeDetectionResumeComposition) evaluates each against its target file.
#
# NEW-kind master_absent_substring verified 0 occurrences on master 2026-05-20:
#   "AT-completion ledger" -> 0  in all three files
#   "workflow.mode"        -> 0  in all three files
#   "per-slice"            -> 0  in all three files
#
# Only ONE MODE_SCOPED clause is shipped (nw-buddy-project-reading,
# roadmap.json) -- it is the single non-vacuous one. The nw-fast-forward
# MODE_SCOPED clause and the nw-at-completeness-check ABSENCE clause from the
# design note are VACUOUS on master (see the module docstring VACUITY AUDIT)
# and are deliberately NOT shipped -- shipping a vacuous clause would be a
# trivially-green non-regression gate.

COHERENCE_CONTRACTS: dict[SkillFile, dict[ClauseKind, CoherenceContract]] = {
    # --- nw-fast-forward -----------------------------------------------------
    SkillFile.FAST_FORWARD: {
        # NEW -- under atdd_pure the resume position is computed from the
        # AT-completion ledger phase-boundary records, NOT execution-log.json.
        # master-absent token: "AT-completion ledger" (0 occurrences).
        # "atdd_pure" co-located so a file naming the ledger without naming the
        # mode is still caught. "phase-boundary" anchors the resume-source
        # mechanism the design note names (L898-899).
        #
        # NOTE: no MODE_SCOPED clause for this file -- master has 0
        # roadmap.json / 0 execution-log lines, so the design note's
        # mode-scope requirement would be vacuous. NEW clause only.
        ClauseKind.NEW: CoherenceContract(
            skill=SkillFile.FAST_FORWARD,
            kind=ClauseKind.NEW,
            present_substrings=(
                "atdd_pure",
                "AT-completion ledger",
                "phase-boundary",
            ),
            master_absent_substring="AT-completion ledger",
            scope_tokens=(),
            qualifier_tokens=(),
        ),
    },
    # --- nw-buddy-project-reading --------------------------------------------
    SkillFile.BUDDY_PROJECT_READING: {
        # NEW -- under atdd_pure, project mode is detected from
        # .nwave/config.yaml:workflow.mode, NOT the presence of roadmap.json.
        # master-absent token: "workflow.mode" (0 occurrences). "atdd_pure"
        # co-located; "AT-completion ledger" is NOT required here (mode
        # detection is a config read, not a ledger read) -- the design note
        # (L900-901) names config.yaml:workflow.mode as the mechanism.
        ClauseKind.NEW: CoherenceContract(
            skill=SkillFile.BUDDY_PROJECT_READING,
            kind=ClauseKind.NEW,
            present_substrings=(
                "atdd_pure",
                "workflow.mode",
            ),
            master_absent_substring="workflow.mode",
            scope_tokens=(),
            qualifier_tokens=(),
        ),
        # MODE_SCOPED -- the ONE non-vacuous mode-scope clause in slice-13.
        # master L92 carries an UNSCOPED `roadmap.json` mention
        # ("`docs/feature/{id}/deliver/roadmap.json`" in the wave-progress
        # table). After slice-13 every roadmap.json line must co-occur with a
        # classic / workflow.mode qualifier (the classic DELIVER path keeps
        # roadmap.json; the atdd_pure path detects via workflow.mode).
        # Non-vacuous: master has 1 unscoped roadmap.json line.
        ClauseKind.MODE_SCOPED: CoherenceContract(
            skill=SkillFile.BUDDY_PROJECT_READING,
            kind=ClauseKind.MODE_SCOPED,
            present_substrings=(),
            master_absent_substring=None,
            scope_tokens=("roadmap.json",),
            qualifier_tokens=_QUALIFIERS,
        ),
    },
    # --- nw-at-completeness-check --------------------------------------------
    SkillFile.AT_COMPLETENESS_CHECK: {
        # NEW -- under atdd_pure, the completeness audit runs against the
        # per-slice AT set, NOT an all-ATs-up-front contract. master-absent
        # token: "per-slice" (0 occurrences). "atdd_pure" co-located.
        #
        # NOTE: no ABSENCE clause for "all ATs up front" -- master has 0
        # occurrences of that framing, so the design note's ABSENCE clause
        # would be vacuous. NEW clause only -- the honest signal is naming the
        # per-slice AT set.
        ClauseKind.NEW: CoherenceContract(
            skill=SkillFile.AT_COMPLETENESS_CHECK,
            kind=ClauseKind.NEW,
            present_substrings=(
                "atdd_pure",
                "per-slice",
            ),
            master_absent_substring="per-slice",
            scope_tokens=(),
            qualifier_tokens=(),
        ),
    },
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

SKILL_FILE_BY_PHRASE: dict[str, SkillFile] = {
    "the nw-fast-forward skill": SkillFile.FAST_FORWARD,
    "the nw-buddy-project-reading skill": SkillFile.BUDDY_PROJECT_READING,
    "the nw-at-completeness-check skill": SkillFile.AT_COMPLETENESS_CHECK,
}
