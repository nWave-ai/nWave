@coupled:slice-04-spine
Feature: The nw-deliver spine branches the whole orchestration flow on workflow mode

  An operator running /nw-deliver on an atdd_pure feature gets the roadmap-free
  spine: no roadmap step, the carpaccio entry gate in place of roadmap creation,
  the per-slice A->G loop, ledger-based audit. An operator running /nw-deliver on
  a classic feature gets the existing roadmap-based DELIVER, byte-for-byte
  unchanged. The two spines are sibling top-level workflows so the orchestrator
  cannot fall through from the atdd_pure path into roadmap creation.

  The scenarios below form one coupled AT group (@coupled:slice-04-spine): the
  spine branch and the slice-class routing are one indivisible orchestration
  contract -- the spine cannot correctly skip roadmap creation without also
  deciding C-vs-P gate routing. coupling_justification recorded in the slice
  plan (feature-delta slice-04 row).

  # ADR-028 D5 / slice-04 of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-04's only deliverable is nWave/skills/nw-deliver/SKILL.md -- a
  # skill/prose orchestration file. It ships NO CLI, NO main(), NO exit code;
  # there is no deterministic runtime that "runs /nw-deliver". The slice-04
  # design note's declared ATs (no roadmap.json/execution-log.json; carpaccio
  # gate invoked; classic unchanged; Phase 6 ledger verification; Class-P
  # routing) are all outcomes of an LLM interpreting the SKILL.md prose -- not
  # mechanically exercisable against an executing system.
  #
  # The honest, mechanically-checkable surface is therefore the SKILL.md
  # CONTENT: a permanent executable coherence test (the Class-P mechanism the
  # rollout's own [REF] Slice classes section mandates for files whose contract
  # is a semantic role -- feature-delta L160-163, slice-10 precedent
  # L621-671). These scenarios assert the spine-branch contract clauses are
  # present in the production SKILL.md with correct mode scoping. This is NOT a
  # fabricated AT-in-the-loop harness -- it asserts real predicates over the
  # real shipped file.
  #
  # Driving surface: the production nw-deliver/SKILL.md content at its repo
  # path (read as-is, Pillar 3). Layer 3 (FS-reading coherence) -- example-only,
  # no PBT (Mandate 9/11). Regression contract: every NEW-clause scenario FAILS
  # on master (the SKILL.md frames atdd_pure as an inner 7-phase replacement,
  # not a whole-spine branch) and PASSES once slice-04 rewrites it into sibling
  # workflows. The one PRESERVATION scenario (Class-P routing) is GREEN on
  # master by design -- it guards that slice-04's rewrite does not DELETE prose
  # slice-03 already shipped.

  Background:
    Given the nw-deliver orchestration spine

  @slice-04 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: The atdd_pure spine branch carries every new mode-conditional contract clause
    When the spine is read for the atdd_pure workflow
    Then the spine <spine clause>
    And that contract clause is new relative to the classic-only master spine

    # slice-04 AT (a-c) + the D5 Phase-6 clause: the four genuinely-NEW
    # spine-branch clauses. Each row's clause carries a master-absent token
    # (verified 0 occurrences on master 2026-05-20), so each row FAILS on
    # master and PASSES after slice-04. AT (d) (Class-P routing) is NOT in this
    # outline -- it is a PRESERVATION clause (slice-03 already shipped the
    # Class-P / coherence-check routing prose, nw-deliver/SKILL.md L92), tested
    # by the dedicated scenario below. The outline parametrize-collapses the
    # four shared-shape new-clause checks into one AT per the max-density
    # mandate. No @walking_skeleton tag: this is a prose-coherence gate, not an
    # end-to-end wiring skeleton (review non-blocking item).
    Examples: the four new spine-branch contract clauses
      | spine clause                                                  |
      | skips roadmap and execution-log creation                      |
      | runs the carpaccio gate in place of roadmap creation           |
      | preserves the classic spine unchanged                          |
      | verifies the ledger and slice-plan and trailers at Phase 6     |

  @slice-04 @driving_port @contract-shape:unbounded-preservation
  Scenario: The Class-P slice routing the spine inherits is preserved, not deleted
    # slice-04 AT (d), reframed honestly (review Blocking 1). The Class-P ->
    # coherence-check routing was shipped by slice-03 (the carpaccio entry_gate
    # note, nw-deliver/SKILL.md L92, which forward-references slice-04 spine
    # routing). Both its tokens -- "Class = P" and "coherence check" -- are
    # already on master. slice-04 rewrites the surrounding spine into sibling
    # top-level workflows; this scenario is the regression guard that the
    # rewrite PRESERVES the inherited Class-P routing rather than dropping it.
    # It is a PRESERVATION contract, GREEN on master by design -- no "new
    # relative to master" assertion, because there is no honest new-vs-master
    # delta to claim.
    When the spine is read for the atdd_pure workflow
    Then the spine skips the carpaccio gate for a prose-coherence slice

  @slice-04 @driving_port @contract-shape:bounded-change
  Scenario: The atdd_pure Setup provisions the AT-completion ledger directory
    When the spine is read for the atdd_pure workflow
    Then the Setup phase provisions the AT-completion ledger directory
    And the per-slice telemetry schema is declared as 1.1.0

  @slice-04 @driving_port @contract-shape:unbounded-preservation
  Scenario: The classic roadmap spine is preserved when the atdd_pure branch is added
    When the spine is read for the classic workflow
    Then the classic roadmap creation phase is still documented
    And the classic spine is named as a sibling top-level workflow
