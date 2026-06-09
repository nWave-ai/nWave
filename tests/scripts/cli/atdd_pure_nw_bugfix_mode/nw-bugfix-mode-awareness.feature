@coupled:slice-05-bugfix-mode
Feature: The nw-bugfix workflow becomes workflow-mode aware

  An operator running /nw-bugfix on an atdd_pure project gets a single-slice fix
  flow with no roadmap: Phase 3 reads workflow.mode, and under atdd_pure a bugfix
  is the canonical single carpaccio slice (regression AT green -> fix -> commit)
  run via the slice-04 roadmap-free spine and the per-slice /nw-execute lean
  cycle. An operator running /nw-bugfix on a classic project gets the existing
  roadmap-based bugfix flow, unchanged.

  The scenarios below form one coupled AT group (@coupled:slice-05-bugfix-mode):
  the mode branch, the atdd_pure single-slice path, and the removal of the stale
  unconditional roadmap wording are one indivisible mode-awareness contract --
  nw-bugfix cannot honestly branch on mode while still telling every operator it
  "creates a minimal roadmap". coupling_justification recorded in the slice plan
  (feature-delta slice-05 row).

  # ADR-028 D5 / slice-05 of the atdd-pure-roadmap-free-rollout (feature-delta
  # ### slice-05 design note, L527-546).
  #
  # CLASS-TYPING + TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL
  # section). slice-05's only deliverable is nWave/skills/nw-bugfix/SKILL.md --
  # a skill/command prose file (user-invocable: true frontmatter -- it is a
  # slash-command instruction set an LLM interprets, not code with a callable
  # surface). It ships NO CLI, NO main(), NO exit code; master vs post-slice
  # differ ONLY in markdown text. Per the refined H3 rule (feature-delta [REF]
  # Slice classes, L224-262) a slice whose ENTIRE deliverable is .md prose is
  # Class P, gated by the executable coherence test -- NOT by @slice-NN
  # behavioural ATs, because none can exist for prose (there is nothing to
  # invoke). The feature-delta already types slice-05 as Class P (slice plan
  # row L35, H3 re-audit row L274).
  #
  # The honest, mechanically-checkable surface is therefore the SKILL.md
  # CONTENT: a permanent executable coherence test (the Class-P mechanism the
  # rollout's own [REF] Slice classes section mandates for files whose contract
  # is a semantic role -- feature-delta L199-202; slice-04 precedent at
  # tests/scripts/cli/atdd_pure_nw_deliver_spine/). These scenarios assert the
  # bugfix-mode contract clauses are present (NEW), removed (ABSENCE), or
  # preserved (PRESERVATION) in the production SKILL.md. This is NOT a
  # fabricated AT-in-the-loop harness -- it asserts real predicates over the
  # real shipped file.
  #
  # Driving surface: the production nw-bugfix/SKILL.md content at its repo path
  # (read as-is, Pillar 3). Layer 3 (FS-reading coherence) -- example-only, no
  # PBT (Mandate 9/11): the clause set is closed and enumerable, realised as a
  # Scenario Outline, NOT a Hypothesis @given. Regression contract: every NEW
  # and ABSENCE scenario FAILS on master (nw-bugfix/SKILL.md is mode-unaware and
  # still says "creates a minimal roadmap") and PASSES once slice-05 lands. The
  # one PRESERVATION scenario is GREEN on master by design -- it guards that
  # slice-05's Phase-3 rewrite does not DELETE the classic two-step flow.

  Background:
    Given the nw-bugfix workflow skill

  @slice-05 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: The bugfix workflow carries every new mode-awareness contract clause
    When the workflow is read for the atdd_pure project mode
    Then the bugfix workflow <bugfix clause>
    And that contract clause is new relative to the mode-unaware master workflow

    # slice-05's three genuinely-NEW clauses. Each row's clause carries a
    # master-absent token verified 0 occurrences on master 2026-05-20
    # (grep -F -c <token> nWave/skills/nw-bugfix/SKILL.md): "workflow.mode" 0,
    # "atdd_pure" 0, "/nw-execute" 0. Each row FAILS on master and PASSES after
    # slice-05. The ABSENCE clause (stale roadmap phrase removed) and the
    # PRESERVATION clause (classic path preserved) are NOT in this outline --
    # they assert a removal and a guard respectively, tested by the dedicated
    # scenarios below. The outline parametrize-collapses the three shared-shape
    # new-clause checks into one AT per the max-density mandate.
    Examples: the three new bugfix-mode contract clauses
      | bugfix clause                                            |
      | reads the workflow mode in Phase 3                       |
      | treats an atdd_pure bugfix as a single carpaccio slice   |
      | runs the atdd_pure bugfix through the per-slice cycle     |

  @slice-05 @driving_port @contract-shape:bounded-change
  Scenario: The stale unconditional roadmap wording is removed
    # slice-05 ABSENCE clause -- the mirror of the NEW clauses. On master
    # nw-bugfix/SKILL.md L108 says "The deliver orchestrator creates a minimal
    # roadmap with 2 steps" UNCONDITIONALLY. Under atdd_pure that is wrong (an
    # atdd_pure bugfix is one carpaccio slice, no roadmap), so the slice-05
    # design note (L542-544, absent_regex: "creates a minimal roadmap") removes
    # the unconditional phrase. This scenario FAILS on master (the phrase is
    # still there) and PASSES once slice-05 deletes it. The bounded-change
    # contract shape: the file's roadmap-creation prose is the bounded mutation
    # set; everything else is preserved (the PRESERVATION scenario guards that).
    When the workflow is read for the atdd_pure project mode
    Then the bugfix workflow no longer unconditionally creates a roadmap

  @slice-05 @driving_port @contract-shape:unbounded-preservation
  Scenario: The classic roadmap-based bugfix path is preserved when the mode branch is added
    # slice-05 PRESERVATION clause. The classic two-step regression-test / fix
    # flow (Step 01-01 Regression test RED, Step 01-02 Fix implementation GREEN)
    # is already on master as the current mode-unaware Phase 3. slice-05 makes
    # it the `classic` branch of the new mode dispatch but must not DELETE it.
    # This scenario is GREEN on master by design -- a regression guard, NO "new
    # relative to master" assertion, because there is no honest new-vs-master
    # delta to claim (slice-04 review Blocking 1: a false absent-on-master claim
    # is forbidden). The present-substrings are tokens true under BOTH the
    # master unconditional framing and the post-slice classic-scoped framing.
    When the workflow is read for the classic project mode
    Then the bugfix workflow preserves the classic roadmap-based bugfix path
