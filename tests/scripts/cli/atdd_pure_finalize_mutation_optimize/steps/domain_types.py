"""Domain types for the finalize/mutation/optimize coherence slice.

slice-09 of the atdd-pure-roadmap-free-rollout (ADR-028 D4.3 + D3).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed
once here as a typed enum / dataclass / NewType. Step bodies and the
composition service consume these typed parameters -- no raw ``str`` where a
domain enum exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-09's only deliverable is the atdd_pure prose added to three cross-wave
finalize-adjacent skill files -- ``nw-finalize``, ``nw-mutation-test``,
``nw-optimize-tests``. All three are skill ``SKILL.md`` prose files: NO CLI,
NO ``main()``, NO exit code; ``master`` vs post-slice-09 differ ONLY in
markdown text. A behavioural / regression AT is structurally impossible --
there is nothing to invoke. Per the refined H3 rule (feature-delta
``[REF] Slice classes``) a slice whose entire deliverable is ``.md`` prose is
Class P, gated by the executable coherence test (feature-delta L743-747,
slice-04 / slice-10 / slice-15 precedent).

THE SLICE-09 CONTRACT -- two clause families, three files
---------------------------------------------------------
slice-09 aligns the three skills with the ATDD-pure roadmap-free spine:

* NEW clauses (``ClauseKind.NEW``) -- each file must NAME the atdd_pure path.
  The slice-09 design note specifies, per file:
    - ``nw-finalize``      -- verify the AT-completion ledger + slice plan +
                              commit-trailer chain (the Phase 6 verification
                              ADR-028 D4.3 specifies).
    - ``nw-mutation-test`` -- scope mutants by the slice's ``at_ids`` from the
                              ledger.
    - ``nw-optimize-tests``-- use the ledger phase-boundary timestamps as the
                              timing baseline.
  Each NEW clause carries a ``master_absent_substring`` VERIFIED 0 occurrences
  on master 2026-05-20 (grep evidence table in the acceptance brief). The
  coherence AT FAILS on master and PASSES once slice-09 lands.

* MODE-SCOPED clauses (``ClauseKind.MODE_SCOPED``) -- the slice-10 semantic-role
  pattern. The design note's "ABSENCE"-style requirement is NOT a bare-token
  absence (``roadmap.json`` / ``execution-log`` legitimately remain for the
  CLASSIC path); it is the falsifiable positive predicate "every line
  mentioning ``roadmap.json`` or ``execution-log`` co-occurs with a
  ``classic`` / ``workflow.mode`` qualifier on the SAME line". An unscoped
  mention implies the roadmap / log is unconditional -- the stale framing
  slice-09 removes.

  VACUITY CHECK (acceptance brief requirement). A MODE-SCOPED clause is
  VACUOUS if the token is already absent / already fully scoped on master.
  Grep evidence 2026-05-20:
    - nw-finalize/SKILL.md     -- 3 roadmap.json + 5 execution-log lines, ALL
                                  unscoped on master (no ``classic`` /
                                  ``workflow.mode`` on the line).
    - nw-mutation-test/SKILL.md-- 7 execution-log lines, ALL unscoped.
    - nw-optimize-tests/SKILL.md- 1 execution-log line, unscoped.
  Every file has >=1 unscoped line on master -- the MODE-SCOPED clause is
  NON-VACUOUS for all three (it genuinely FAILS on master). No vacuous-clause
  flag is raised.

WHY a SEPARATE test directory
-----------------------------
slices 04 and 15 ship coherence tests over ``nw-deliver/SKILL.md``; slice-09's
three files are disjoint from those. ``atdd_pure_finalize_mutation_optimize``
is the slice-09-scoped directory (underscores, per the directory-naming
mandate).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a skill / doc file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class SkillFile(str, Enum):
    """The three slice-09 finalize-adjacent skill files under coherence audit.

    Each value is the repo-root-relative path to the production ``SKILL.md``.
    The composition reads the real shipped file (Pillar 3: app as in
    production -- no hand-built fixture copy).
    """

    FINALIZE = "nWave/skills/nw-finalize/SKILL.md"
    MUTATION_TEST = "nWave/skills/nw-mutation-test/SKILL.md"
    OPTIMIZE_TESTS = "nWave/skills/nw-optimize-tests/SKILL.md"


class ClauseKind(str, Enum):
    """Whether a slice-09 coherence clause is a NEW-prose or a MODE-SCOPED check.

    NEW         -- the clause's prose is genuinely added by slice-09. The
                   contract carries a ``master_absent_substring`` VERIFIED
                   absent on master; the coherence AT FAILS on master and
                   PASSES once slice-09 lands (regression-AT contract).
    MODE_SCOPED -- the clause is a semantic-role predicate (slice-10 pattern):
                   every line mentioning a roadmap / execution-log token must
                   co-occur with a ``classic`` / ``workflow.mode`` qualifier.
                   It carries NO ``master_absent_substring`` (the token is
                   legitimately present for the classic path); its
                   regression signal is the per-line scoping check, which is
                   NON-VACUOUS only when master has >=1 unscoped line.
    """

    NEW = "new"
    MODE_SCOPED = "mode_scoped"


@dataclass(frozen=True)
class CoherenceContract:
    """A single coherence assertion over one slice-09 skill file.

    ``skill``       -- which of the three slice-09 files this clause governs.
    ``kind``        -- NEW or MODE_SCOPED.
    ``present_substrings``
                    -- domain tokens that MUST all appear in the file once
                       slice-09 lands. For a NEW clause these are the new
                       atdd_pure prose tokens; for a MODE_SCOPED clause this
                       is empty (a mode-scoped clause asserts a per-line
                       property, not bare presence).
    ``master_absent_substring``
                    -- for a NEW clause, one token VERIFIED 0 occurrences on
                       master, proving the clause is genuinely new (the AT
                       FAILS on master, PASSES after slice-09). REQUIRED for
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
    Blocking 1 precedent).
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
                    f"present_substrings (the slice-09 prose adds it)"
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


# The slice-09 coherence contracts. The composition service
# (FinalizeMutationOptimizeComposition) evaluates each against its target file.
#
# Every NEW-kind master_absent_substring was verified 0 occurrences on master
# 2026-05-20 (`grep -cF <token> nWave/skills/nw-{...}/SKILL.md`):
#   "atdd_pure"              -> 0  in all three files
#   "AT-completion ledger"   -> 0  in all three files
# The MODE_SCOPED scope tokens were verified PRESENT-AND-UNSCOPED on master
# (>=1 line each, no `classic` / `workflow.mode` qualifier) -- so the per-line
# check is non-vacuous: nw-finalize 3+5 lines, nw-mutation-test 7 lines,
# nw-optimize-tests 1 line. See the acceptance brief grep evidence table.

# The two qualifier tokens that scope a roadmap / execution-log line to the
# classic path. Either one on the line satisfies the mode-scope predicate.
_QUALIFIERS: tuple[str, ...] = ("classic", "workflow.mode")

# The roadmap / execution-log tokens whose every occurrence line must be
# classic-scoped after slice-09.
_ROADMAP_LOG_TOKENS: tuple[str, ...] = ("roadmap.json", "execution-log")


COHERENCE_CONTRACTS: dict[SkillFile, dict[ClauseKind, CoherenceContract]] = {
    # --- nw-finalize ---------------------------------------------------------
    SkillFile.FINALIZE: {
        # NEW -- atdd_pure Phase 6 verification (ADR-028 D4.3): verify the
        # AT-completion ledger + slice plan + commit-trailer chain.
        # master-absent token: "AT-completion ledger" (0 occurrences).
        # "atdd_pure" co-located so a file naming the ledger without naming
        # the mode is still caught. "slice plan" anchors the D4.3 triple.
        ClauseKind.NEW: CoherenceContract(
            skill=SkillFile.FINALIZE,
            kind=ClauseKind.NEW,
            present_substrings=(
                "atdd_pure",
                "AT-completion ledger",
                "slice plan",
            ),
            master_absent_substring="AT-completion ledger",
            scope_tokens=(),
            qualifier_tokens=(),
        ),
        # MODE_SCOPED -- every roadmap.json / execution-log line is
        # classic-scoped. Non-vacuous: master has 3 roadmap.json + 5
        # execution-log unscoped lines.
        ClauseKind.MODE_SCOPED: CoherenceContract(
            skill=SkillFile.FINALIZE,
            kind=ClauseKind.MODE_SCOPED,
            present_substrings=(),
            master_absent_substring=None,
            scope_tokens=_ROADMAP_LOG_TOKENS,
            qualifier_tokens=_QUALIFIERS,
        ),
    },
    # --- nw-mutation-test ----------------------------------------------------
    SkillFile.MUTATION_TEST: {
        # NEW -- under atdd_pure, scope mutants by the slice's at_ids from the
        # ledger. master-absent token: "AT-completion ledger" (0 occurrences).
        # "at_ids" anchors the mutant-scoping mechanism the design note names.
        ClauseKind.NEW: CoherenceContract(
            skill=SkillFile.MUTATION_TEST,
            kind=ClauseKind.NEW,
            present_substrings=(
                "atdd_pure",
                "AT-completion ledger",
                "at_ids",
            ),
            master_absent_substring="AT-completion ledger",
            scope_tokens=(),
            qualifier_tokens=(),
        ),
        # MODE_SCOPED -- every execution-log line is classic-scoped.
        # Non-vacuous: master has 7 unscoped execution-log lines.
        ClauseKind.MODE_SCOPED: CoherenceContract(
            skill=SkillFile.MUTATION_TEST,
            kind=ClauseKind.MODE_SCOPED,
            present_substrings=(),
            master_absent_substring=None,
            scope_tokens=_ROADMAP_LOG_TOKENS,
            qualifier_tokens=_QUALIFIERS,
        ),
    },
    # --- nw-optimize-tests ---------------------------------------------------
    SkillFile.OPTIMIZE_TESTS: {
        # NEW -- under atdd_pure, use the ledger phase-boundary timestamps as
        # the timing baseline. master-absent token: "AT-completion ledger"
        # (0 occurrences). "phase-boundary" anchors the timing-baseline source.
        ClauseKind.NEW: CoherenceContract(
            skill=SkillFile.OPTIMIZE_TESTS,
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
        # MODE_SCOPED -- every execution-log line is classic-scoped.
        # Non-vacuous: master has 1 unscoped execution-log line.
        ClauseKind.MODE_SCOPED: CoherenceContract(
            skill=SkillFile.OPTIMIZE_TESTS,
            kind=ClauseKind.MODE_SCOPED,
            present_substrings=(),
            master_absent_substring=None,
            scope_tokens=_ROADMAP_LOG_TOKENS,
            qualifier_tokens=_QUALIFIERS,
        ),
    },
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

SKILL_FILE_BY_PHRASE: dict[str, SkillFile] = {
    "the nw-finalize skill": SkillFile.FINALIZE,
    "the nw-mutation-test skill": SkillFile.MUTATION_TEST,
    "the nw-optimize-tests skill": SkillFile.OPTIMIZE_TESTS,
}
