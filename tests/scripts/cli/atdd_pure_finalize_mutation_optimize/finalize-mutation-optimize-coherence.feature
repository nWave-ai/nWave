@coupled:slice-09-finalize-mutation-optimize
Feature: The finalize-adjacent skills document the atdd_pure roadmap-free path

  An operator running /nw-finalize (or mutation testing, or test optimization)
  on an atdd_pure feature gets ledger + slice-plan + commit-trailer
  verification, never roadmap.json / execution-log as required input.
  slice-09 ships this prose into three finalize-adjacent skill files:
  nw-finalize, nw-mutation-test, nw-optimize-tests.

  The scenarios below form one coupled AT group
  (@coupled:slice-09-finalize-mutation-optimize): the three skills' atdd_pure
  alignment is one indivisible coherence contract -- a finalize flow that
  names the AT-completion ledger but a mutation flow still rooted in the
  execution-log would ship a half-aligned feature-end surface.
  coupling_justification recorded in the slice plan (feature-delta slice-09
  row).

  # ADR-028 D4.3 + D3 / slice-09 of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-09's only deliverable is the atdd_pure prose added to three skill
  # SKILL.md files. They ship NO CLI, NO main(), NO exit code; master vs
  # post-slice-09 differ ONLY in markdown text. A behavioural / regression AT
  # is structurally impossible -- there is nothing to invoke. Per the refined
  # H3 rule a slice whose entire deliverable is .md prose is Class P, gated by
  # the executable coherence test.
  #
  # SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md): slice-09
  # targets three disjoint files. This .feature asserts ONLY the slice-09
  # contract clauses.
  #
  # Driving surface: the production SKILL.md content at its repo path (read
  # as-is, Pillar 3). Layer 3 (FS-reading coherence) -- example-only, no PBT
  # (Mandate 9/11). Two clause families:
  #
  #  * NEW clauses -- each file must NAME the atdd_pure path (the AT-completion
  #    ledger + the per-file mechanism: nw-finalize -> slice-plan + trailer
  #    verification; nw-mutation-test -> at_ids mutant scoping; nw-optimize-
  #    tests -> phase-boundary timing baseline). master-absent token verified
  #    0 occurrences 2026-05-20 -> each FAILS on master, PASSES after slice-09.
  #
  #  * MODE-SCOPED clause -- the slice-10 semantic-role pattern. Every line
  #    mentioning roadmap.json / execution-log must co-occur with a classic /
  #    workflow.mode qualifier. NON-VACUOUS: master carries unscoped lines in
  #    all three files (nw-finalize 8, nw-mutation-test 7, nw-optimize-tests
  #    1) -> the per-line check genuinely FAILS on master.

  Background:
    Given a finalize-adjacent skill

  @slice-09 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every finalize-adjacent skill names the atdd_pure roadmap-free path
    When <skill> is read for the atdd_pure workflow
    Then <skill> names the atdd_pure AT-completion-ledger path
    And that atdd_pure prose is new relative to the classic-only master skill

    # The three slice-09 NEW clauses, one per file. Each carries a
    # master-absent token ("AT-completion ledger", verified 0 occurrences on
    # master in every file 2026-05-20), so each row FAILS on master and PASSES
    # once slice-09 adds the prose. The outline parametrize-collapses the three
    # shared-shape new-clause checks into one AT per the max-density mandate.
    Examples: the three finalize-adjacent skills
      | skill                       |
      | the nw-finalize skill       |
      | the nw-mutation-test skill  |
      | the nw-optimize-tests skill |

  @slice-09 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every roadmap or execution-log mention is scoped to the classic path
    When <skill> is read for the atdd_pure workflow
    Then every roadmap or execution-log line in <skill> is classic-scoped

    # MODE-SCOPED clause (slice-10 semantic-role pattern). The roadmap.json /
    # execution-log tokens legitimately REMAIN in each file for the classic
    # path -- a bare-token absence assertion would be wrong. The contract is
    # the falsifiable positive predicate "every such line co-occurs with a
    # classic / workflow.mode qualifier". NON-VACUOUS: master carries unscoped
    # lines in all three files, so each row genuinely FAILS on master and
    # PASSES once slice-09 scopes the prose.
    Examples: the three finalize-adjacent skills
      | skill                       |
      | the nw-finalize skill       |
      | the nw-mutation-test skill  |
      | the nw-optimize-tests skill |
