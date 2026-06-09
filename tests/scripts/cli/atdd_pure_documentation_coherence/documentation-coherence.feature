@coupled:slice-12-documentation-coherence
Feature: The reference / tutorial / wave-flow docs document the atdd_pure roadmap-free path

  A reader of the des-markers reference, the deliver-feature tutorial, or the
  wave-flow precise map must find the atdd_pure roadmap-free workflow
  documented alongside the retained classic path -- the AT-completion ledger
  marker, the atdd_pure deliver tutorial, and the carpaccio slicing model.
  slice-12 ships this prose into three documentation files:
  docs/reference/des-markers.md, docs/guides/tutorial-deliver-feature/README.md,
  docs/analysis/wave-flow-precise-map.md.

  The scenarios below form one coupled AT group
  (@coupled:slice-12-documentation-coherence): the three docs' atdd_pure
  alignment is one indivisible coherence contract -- a marker reference that
  names the AT-completion ledger but a tutorial still silent on atdd_pure
  would ship a half-documented operator surface.

  # ADR-028 / ADR-029 / slice-12 of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-12's only deliverable is the atdd_pure documentation prose added to
  # three .md doc files. They ship NO CLI, NO main(), NO exit code; master vs
  # post-slice-12 differ ONLY in markdown text. A behavioural / regression AT
  # is structurally impossible -- there is nothing to invoke. Per the refined
  # H3 rule (feature-delta L883-893) a slice whose entire deliverable is .md
  # prose is Class P, gated by the executable coherence test. H3 discriminator
  # (feature-delta L878-880): pure documentation, unambiguously no runtime
  # read.
  #
  # SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md),
  # slice-09 (the three finalize-adjacent skills), slice-11 (the roadmap
  # skill / command / root-why skill), and slice-13 (the three mode/resume/
  # AT-set skills): slice-12 targets three disjoint files. This .feature
  # asserts ONLY the slice-12 contract clauses.
  #
  # Driving surface: the production .md content at its repo path (read as-is,
  # Pillar 3). Layer 3 (FS-reading coherence) -- example-only, no PBT
  # (Mandate 9/11).
  #
  # ONE clause family: NEW literal-regex clauses. The design-note 3-row table
  # (feature-delta L870-872) is fully ADDITIVE -- the atdd_pure path is
  # documented alongside the retained classic path; every row has an empty
  # absent_regex and a single present_regex. Each file must MATCH its
  # present_regex once slice-12 lands. Each present_regex is verified 0
  # matches on master 2026-05-20 -> each FAILS on master, PASSES after
  # slice-12. No vacuous clause -- all three regexes are non-vacuous.
  #
  #   des-markers.md                      -> present_regex  AT-completion ledger
  #   tutorial-deliver-feature/README.md  -> present_regex  atdd_pure
  #   wave-flow-precise-map.md            -> present_regex  carpaccio
  #
  # wave-flow-precise-map.md is under docs/analysis/ (internal,
  # public-sync-excluded) -- still in scope, it must not mislead internal
  # readers (feature-delta L880-881).

  Background:
    Given a reference / tutorial / wave-flow doc

  @slice-12 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every reference / tutorial / wave-flow doc carries its slice-12 atdd_pure prose
    When <doc> is read for the atdd_pure workflow
    Then <doc> matches its slice-12 atdd_pure documentation regex

    # The three slice-12 NEW clauses, one per file. Each carries a
    # present_regex verified 0 matches on master 2026-05-20
    # ("AT-completion ledger" for des-markers, "atdd_pure" for the deliver
    # tutorial, "carpaccio" for the wave-flow map), so each row FAILS on
    # master and PASSES once slice-12 adds the prose. The outline
    # parametrize-collapses the three shared-shape new-clause checks into one
    # AT per the max-density mandate.
    Examples: the three reference / tutorial / wave-flow docs
      | doc                            |
      | the des-markers reference      |
      | the deliver-feature tutorial   |
      | the wave-flow precise map      |
