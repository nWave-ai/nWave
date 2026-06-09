@coupled:slice-15-feature-end-cycle
Feature: The nw-deliver atdd_pure spine documents the once-per-feature feature-end cycle

  An operator running /nw-deliver on an atdd_pure feature, after the last slice
  ships, gets ONE feature-end cycle: a whole-feature E_BATCH_REFACTOR (L1-L6,
  batch-then-verify), a deep adversarial review that collapses C_REVIEWER_AUDIT
  and F_FINAL_REVIEW into one review of the coherent finished feature, then
  final integrity verification. An operator who interrupts that closing pass and
  later runs /nw-continue resumes it at the recorded feature-end-cycle
  checkpoint. slice-15 ships this prose into nw-deliver/SKILL.md.

  The scenarios below form one coupled AT group
  (@coupled:slice-15-feature-end-cycle): the feature-end cycle, its collapsed
  deep review, and the checkpoint-based resume cue are one indivisible D6
  orchestration contract -- a feature-end cycle prose that names the cycle but
  not its resume cue would ship a non-resumable closing pass. coupling_
  justification recorded in the slice plan (feature-delta slice-15 row).

  # ADR-028 D6 / slice-15 of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-15's only deliverable is the D6 feature-end-cycle prose added to
  # nWave/skills/nw-deliver/SKILL.md -- a skill/prose orchestration file. It
  # ships NO CLI, NO main(), NO exit code; master vs post-slice-15 differ ONLY
  # in markdown text. A behavioural/regression AT is structurally impossible.
  # Per the refined H3 rule a slice whose entire deliverable is .md prose is
  # Class P, gated by the executable coherence test.
  #
  # SEPARATE from slice-04's atdd_pure_nw_deliver_spine coherence test: that
  # shipped test (commit 8d78f5c6c) gates the per-slice spine contract over the
  # same file. slice-15 ships the feature-end-cycle prose -- a named,
  # separately-committed Class-P slice (feature-delta L915-952, follow-up note
  # HIGH-2/HIGH-3). This .feature asserts ONLY the feature-end-cycle clauses; it
  # does NOT duplicate slice-04's per-slice-spine clauses. The one PRESERVATION
  # scenario is the cross-slice guard that slice-15's edit does not DELETE
  # slice-04's per-slice spine prose.
  #
  # Driving surface: the production nw-deliver/SKILL.md content at its repo path
  # (read as-is, Pillar 3). Layer 3 (FS-reading coherence) -- example-only, no
  # PBT (Mandate 9/11). Regression contract: every NEW-clause scenario FAILS on
  # master (the SKILL.md frames E_BATCH_REFACTOR / C_REVIEWER_AUDIT /
  # F_FINAL_REVIEW only as PER-SLICE A->G phases, with NO once-per-feature
  # feature-end cycle) and PASSES once slice-15 adds the prose. The one
  # PRESERVATION scenario is GREEN on master by design.

  Background:
    Given the nw-deliver orchestration spine

  @slice-15 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: The atdd_pure spine prose carries every new feature-end-cycle contract clause
    When the spine is read for the atdd_pure workflow
    Then the spine <feature-end clause>
    And that contract clause is new relative to the per-slice-only master spine

    # slice-15 NEW clauses: the three genuinely-new feature-end-cycle clauses.
    # Each row's clause carries a master-absent token (verified 0 occurrences
    # on master 2026-05-20), so each row FAILS on master and PASSES after
    # slice-15. The PRESERVATION clause (slice-04 per-slice spine guard) is NOT
    # in this outline -- it is tested by the dedicated scenario below. The
    # outline parametrize-collapses the three shared-shape new-clause checks
    # into one AT per the max-density mandate.
    Examples: the three new feature-end-cycle contract clauses
      | feature-end clause                                                  |
      | defines a once-per-feature feature-end cycle after the last slice    |
      | collapses the deep review and runs final integrity verification     |
      | records a feature-end-cycle checkpoint for /nw-continue resume       |

  @slice-15 @driving_port @contract-shape:unbounded-preservation
  Scenario: The slice-04 per-slice spine prose is preserved, not deleted
    # slice-15 cross-slice regression guard (Pillar 2: chained narrative).
    # slice-04 (commit 8d78f5c6c) shipped the per-slice spine prose -- the
    # "ATDD-Pure Roadmap-Free Spine" section and the per-slice A->G loop --
    # into the same file. slice-15 ADDS the feature-end-cycle prose ALONGSIDE
    # it. Both this clause's tokens are already on master. This scenario is the
    # regression guard that slice-15's edit PRESERVES slice-04's per-slice
    # spine rather than overwriting it. It is a PRESERVATION contract, GREEN on
    # master by design -- no "new relative to master" assertion, because there
    # is no honest new-vs-master delta to claim.
    When the spine is read for the atdd_pure workflow
    Then the spine preserves the slice-04 per-slice spine prose
