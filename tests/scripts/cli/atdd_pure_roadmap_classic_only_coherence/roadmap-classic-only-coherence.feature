@coupled:slice-11-roadmap-classic-only-coherence
Feature: The roadmap skill / command flag classic-mode-only and nw-root-why names the atdd_pure ledger

  An operator reading the roadmap skill, the roadmap command, or the
  nw-root-why skill must see that roadmap authoring is a classic-mode-only
  activity -- the atdd_pure roadmap-free workflow does not use a roadmap --
  and that root-cause analysis under atdd_pure is rooted in the per-slice
  ledger. slice-11 ships this prose into three production files:
  nw-roadmap/SKILL.md, nw/roadmap.md, nw-root-why/SKILL.md.

  The scenarios below form one coupled AT group
  (@coupled:slice-11-roadmap-classic-only-coherence): the three files'
  atdd_pure alignment is one indivisible coherence contract -- a roadmap
  skill flagged classic-only but a roadmap command still silent on the
  atdd_pure workflow would ship a half-aligned operator surface.

  # ADR-028 / ADR-029 / slice-11 of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-11's only deliverable is the classic-only / atdd_pure-context prose
  # added to three .md files. They ship NO CLI, NO main(), NO exit code;
  # master vs post-slice-11 differ ONLY in markdown text. A behavioural /
  # regression AT is structurally impossible -- there is nothing to invoke.
  # Per the refined H3 rule (feature-delta L883-893) a slice whose entire
  # deliverable is .md prose is Class P, gated by the executable coherence
  # test. H3 discriminator (feature-delta L858-859): all three files carry
  # only stale description; no orchestrator reads them to branch.
  #
  # SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md),
  # slice-09 (the three finalize-adjacent skills), and slice-13 (the three
  # mode/resume/AT-set skills): slice-11 targets three disjoint files. This
  # .feature asserts ONLY the slice-11 contract clauses.
  #
  # Driving surface: the production .md content at its repo path (read as-is,
  # Pillar 3). Layer 3 (FS-reading coherence) -- example-only, no PBT
  # (Mandate 9/11).
  #
  # ONE clause family: NEW literal-regex clauses. The design-note 3-row table
  # (feature-delta L847-849) is fully ADDITIVE -- every row has an empty
  # absent_regex and a single present_regex. Each file must MATCH its
  # present_regex once slice-11 lands. Each present_regex is verified 0
  # matches on master 2026-05-20 -> each FAILS on master, PASSES after
  # slice-11. No vacuous clause -- all three regexes are non-vacuous.
  #
  #   nw-roadmap/SKILL.md   -> present_regex  classic mode only
  #   nw/roadmap.md         -> present_regex  not used under .*atdd_pure
  #   nw-root-why/SKILL.md  -> present_regex  atdd_pure.*slice.*ledger

  Background:
    Given a roadmap-or-root-why file

  @slice-11 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every roadmap / root-why file carries its slice-11 atdd_pure flag
    When <file> is read for the atdd_pure workflow
    Then <file> matches its slice-11 classic-only-or-atdd_pure-context regex

    # The three slice-11 NEW clauses, one per file. Each carries a
    # present_regex verified 0 matches on master 2026-05-20
    # ("classic mode only" for nw-roadmap, "not used under .*atdd_pure" for
    # nw/roadmap.md, "atdd_pure.*slice.*ledger" for nw-root-why), so each row
    # FAILS on master and PASSES once slice-11 adds the prose. The outline
    # parametrize-collapses the three shared-shape new-clause checks into one
    # AT per the max-density mandate.
    Examples: the three roadmap / root-why files
      | file                     |
      | the nw-roadmap skill     |
      | the nw-roadmap command   |
      | the nw-root-why skill    |
