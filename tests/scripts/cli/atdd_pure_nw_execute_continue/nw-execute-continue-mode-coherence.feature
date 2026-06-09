@coupled:slice-08-execute-continue-mode
Feature: The nw-execute and nw-continue orchestration docs become workflow-mode aware

  An operator running /nw-execute on an atdd_pure feature gets the per-slice lean
  cycle -- ONE carpaccio slice through the carpaccio entry gate, A_GREEN_ATS,
  B_COVERAGE_CLEANUP, a light slice review, the terminating contract-gate run and
  G_COMMIT -- never roadmap-step extraction or execution-log emission. An operator
  running /nw-continue on an atdd_pure feature resumes a /nw-deliver run with the
  two-case cue: still-pending slices restart the /nw-execute loop at the first
  un-shipped slice; all-shipped slices resume the feature-end cycle from the
  latest FeatureEndCheckpoint ledger record. An operator on a classic project
  gets the existing roadmap-step / execution-log flow, unchanged.

  The scenarios below form one coupled AT group
  (@coupled:slice-08-execute-continue-mode): the execute redefinition, the
  continue two-case resume cue, and the mode-scoping of every roadmap.json /
  execution-log mention are one indivisible mode-coherence contract -- the four
  orchestration docs cannot honestly branch on mode while still telling every
  operator, unconditionally, to extract roadmap steps and emit an execution-log.
  coupling_justification recorded in the slice plan (feature-delta slice-08 row).

  # ADR-028 D6 / slice-08 of the atdd-pure-roadmap-free-rollout (feature-delta
  # ### slice-08 design note, L685-725).
  #
  # CLASS-TYPING + TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL
  # section). slice-08's four deliverables are all .md prose -- two skill
  # SKILL.md files (nw-execute, nw-continue) and two command task docs
  # (nw/execute.md, nw/continue.md). None ships a CLI, a main(), or an exit
  # code; master vs post-slice differ ONLY in markdown text. The executable
  # mechanics the prose describes (per-slice A->G dispatch, the AT-completion
  # ledger, the carpaccio gate) are shipped by the Class-C slices 01-03/14, not
  # here. Per the refined H3 rule (feature-delta [REF] Slice classes, L224-262)
  # a slice whose ENTIRE deliverable is .md prose is Class P, gated by the
  # executable coherence test -- NOT by @slice-NN behavioural ATs, because none
  # can exist for prose (there is nothing to invoke). The feature-delta already
  # types slice-08 as Class P (slice plan row L38, H3 re-audit row L277).
  #
  # The honest, mechanically-checkable surface is therefore the doc CONTENT: a
  # permanent executable coherence test (the Class-P mechanism the rollout's own
  # [REF] Slice classes section mandates -- feature-delta L199-202; slice-04 /
  # slice-05 precedents). These scenarios assert the mode-coherence contract
  # clauses are present (NEW) or mode-scoped (MODE_SCOPED) in the production
  # files. This is NOT a fabricated AT-in-the-loop harness -- it asserts real
  # predicates over the four real shipped files.
  #
  # Driving surface: the production nw-execute / nw-continue SKILL.md + task
  # docs at their repo paths (read as-is, Pillar 3). Layer 3 (FS-reading
  # coherence) -- example-only, no PBT (Mandate 9/11): the clause set is closed
  # and enumerable, realised as Scenario Outlines, NOT a Hypothesis @given.
  # Regression contract: every NEW and MODE_SCOPED scenario FAILS on master
  # (the four docs are mode-unaware and mention roadmap.json / execution-log
  # unscoped) and PASSES once slice-08 lands.
  #
  # DESIGN-NOTE DISCREPANCY (reported in the acceptance brief). The design note
  # (L721-722) says "every roadmap / execution-log mention co-occurs with a
  # qualifier" for all four files. master nw-continue (SKILL + task doc) has
  # ZERO roadmap.json occurrences, so a roadmap MODE_SCOPED clause for the
  # continue pair would be vacuously satisfied on master (no line to qualify)
  # -- a non-falsifiable, non-regression assertion. Per slice-04 review
  # Blocking-1 discipline the continue pair carries an execution-log
  # MODE_SCOPED clause ONLY; the execute pair carries both. Every MODE_SCOPED
  # scenario below genuinely FAILS on master.

  @slice-08 @driving_port @contract-shape:bounded-change
  Scenario Outline: The execute orchestration docs carry every new per-slice-cycle clause
    Given <execute doc>
    When the orchestration doc is read for the atdd_pure project mode
    Then the execute orchestration doc <execute clause>
    And that contract clause is new relative to the mode-unaware master doc

    # slice-08's three genuinely-NEW execute-pair clauses, run against BOTH the
    # nw-execute SKILL and the nw/execute task doc. Each clause carries a
    # master-absent token verified 0 occurrences on master 2026-05-20
    # (grep -F -c <token>): "workflow.mode" 0, "per-slice lean cycle" 0,
    # "A_GREEN_ATS" 0, on both files. Each row FAILS on master and PASSES after
    # slice-08. The outline parametrize-collapses the 2 docs x 3 clauses = 6
    # shared-shape new-clause checks into one AT (max-density mandate).
    Examples: the execute pair x the three new per-slice-cycle clauses
      | execute doc                  | execute clause                                            |
      | the nw-execute skill         | reads the workflow mode                                   |
      | the nw-execute skill         | runs the per-slice lean cycle under atdd_pure             |
      | the nw-execute skill         | runs A_GREEN_ATS through the carpaccio gate under atdd_pure |
      | the nw-execute command doc   | reads the workflow mode                                   |
      | the nw-execute command doc   | runs the per-slice lean cycle under atdd_pure             |
      | the nw-execute command doc   | runs A_GREEN_ATS through the carpaccio gate under atdd_pure |

  @slice-08 @driving_port @contract-shape:bounded-change
  Scenario Outline: The continue orchestration docs carry every new two-case resume cue
    Given <continue doc>
    When the orchestration doc is read for the atdd_pure project mode
    Then the continue orchestration doc <continue clause>
    And that contract clause is new relative to the mode-unaware master doc

    # slice-08's three genuinely-NEW continue-pair clauses, run against BOTH the
    # nw-continue SKILL and the nw/continue task doc. master-absent tokens
    # verified 0 occurrences 2026-05-20: "workflow.mode" 0, "un-shipped slice"
    # 0, "FeatureEndCheckpoint" 0, on both files. The two resume cases (case i
    # un-shipped slice, case ii FeatureEndCheckpoint) are asserted as separate
    # clauses so a continue doc that adds an atdd_pure branch covering only one
    # case is still caught. 2 docs x 3 clauses = 6 checks, one AT.
    Examples: the continue pair x the three new resume-cue clauses
      | continue doc                  | continue clause                                                     |
      | the nw-continue skill         | reads the workflow mode                                              |
      | the nw-continue skill         | resumes at the first un-shipped slice under atdd_pure                |
      | the nw-continue skill         | resumes the feature-end cycle from the checkpoint under atdd_pure    |
      | the nw-continue command doc   | reads the workflow mode                                              |
      | the nw-continue command doc   | resumes at the first un-shipped slice under atdd_pure                |
      | the nw-continue command doc   | resumes the feature-end cycle from the checkpoint under atdd_pure    |

  @slice-08 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every roadmap and execution-log mention is scoped to the classic mode
    Given <orchestration doc>
    When the orchestration doc is read for the classic project mode
    Then every line mentioning <legacy artifact> is scoped to a workflow mode

    # slice-08's MODE_SCOPED clauses -- the per-line semantic-role predicate
    # (slice-10 pattern). The contract is NOT "remove roadmap.json /
    # execution-log" (those are legitimate under classic) but "every line
    # carrying the token also carries a classic / workflow.mode qualifier". On
    # master every such line is unqualified (0 qualifier occurrences across all
    # four files 2026-05-20), so every row FAILS on master and PASSES once
    # slice-08 mode-scopes the lines. The execute pair carries BOTH roadmap.json
    # and execution-log (both present-and-unscoped on master); the continue
    # pair carries execution-log ONLY -- roadmap.json is 0 on master nw-continue,
    # a roadmap clause there would be vacuously true (non-falsifiable). The
    # unbounded-preservation contract shape: the classic-mode prose is
    # preserved, the mutation is the bounded addition of a per-line qualifier.
    Examples: the legacy-artifact mentions that must be mode-scoped
      | orchestration doc             | legacy artifact   |
      | the nw-execute skill          | the roadmap file  |
      | the nw-execute skill          | the execution log |
      | the nw-execute command doc    | the roadmap file  |
      | the nw-execute command doc    | the execution log |
      | the nw-continue skill         | the execution log |
      | the nw-continue command doc   | the execution log |
