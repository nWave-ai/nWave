@coupled:slice-13-mode-detection-resume-coherence
Feature: The mode/resume/AT-set skills document the atdd_pure roadmap-free path

  An operator working an atdd_pure feature gets resume, project-mode
  detection, and AT-set auditing rooted in the AT-completion ledger,
  .nwave/config.yaml:workflow.mode, and the per-slice AT set -- never
  roadmap.json, the execution-log, or an all-ATs-up-front contract.
  slice-13 ships this prose into three skill files: nw-fast-forward,
  nw-buddy-project-reading, nw-at-completeness-check.

  The scenarios below form one coupled AT group
  (@coupled:slice-13-mode-detection-resume-coherence): the three skills'
  atdd_pure alignment is one indivisible coherence contract -- a resume flow
  that names the AT-completion ledger but a project-mode detector still
  rooted in roadmap.json would ship a half-aligned operator surface.

  # ADR-028 / ADR-029 / slice-13 of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-13's only deliverable is the atdd_pure prose added to three skill
  # SKILL.md files. They ship NO CLI, NO main(), NO exit code; master vs
  # post-slice-13 differ ONLY in markdown text. A behavioural / regression AT
  # is structurally impossible -- there is nothing to invoke. Per the refined
  # H3 rule (feature-delta L883-893) a slice whose entire deliverable is .md
  # prose is Class P, gated by the executable coherence test. The data
  # artifacts the skills DESCRIBE reading (the AT-completion ledger,
  # workflow.mode, the per-slice AT set) are created by the CLIs of slices
  # 01-03, NOT by these skill files.
  #
  # SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md) and
  # slice-09 (the three finalize-adjacent skills): slice-13 targets three
  # disjoint files. This .feature asserts ONLY the slice-13 contract clauses.
  #
  # Driving surface: the production SKILL.md content at its repo path (read
  # as-is, Pillar 3). Layer 3 (FS-reading coherence) -- example-only, no PBT
  # (Mandate 9/11). Two clause families:
  #
  #  * NEW clauses -- each file must NAME the atdd_pure path (the per-file
  #    mechanism: nw-fast-forward -> AT-completion ledger phase-boundary
  #    resume; nw-buddy-project-reading -> .nwave/config.yaml:workflow.mode
  #    mode detection; nw-at-completeness-check -> per-slice AT set audit).
  #    master-absent token verified 0 occurrences 2026-05-20 -> each FAILS on
  #    master, PASSES after slice-13.
  #
  #  * MODE-SCOPED clause -- the slice-09 / slice-10 semantic-role pattern.
  #    ONLY nw-buddy-project-reading has a non-vacuous one: master L92 carries
  #    an unscoped roadmap.json mention. After slice-13 every roadmap.json
  #    line co-occurs with a classic / workflow.mode qualifier.
  #
  # VACUOUS DESIGN-NOTE CLAUSES NOT SHIPPED (acceptance brief flags):
  #   - nw-fast-forward MODE-SCOPED (roadmap.json / execution-log scoping):
  #     master has 0 such lines -> a per-line check over zero lines is
  #     trivially green -> not a regression signal. NEW clause only.
  #   - nw-at-completeness-check ABSENCE ("all ATs up front" framing): master
  #     has 0 occurrences of that token -> an ABSENCE clause needs the token
  #     PRESENT to be non-vacuous. NEW clause only.

  Background:
    Given a mode-detection / resume / AT-set skill

  @slice-13 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every mode/resume/AT-set skill names the atdd_pure roadmap-free path
    When <skill> is read for the atdd_pure workflow
    Then <skill> names the atdd_pure roadmap-free mechanism
    And that atdd_pure prose is new relative to the classic-only master skill

    # The three slice-13 NEW clauses, one per file. Each carries a
    # master-absent token (verified 0 occurrences on master 2026-05-20:
    # "AT-completion ledger" for nw-fast-forward, "workflow.mode" for
    # nw-buddy-project-reading, "per-slice" for nw-at-completeness-check), so
    # each row FAILS on master and PASSES once slice-13 adds the prose. The
    # outline parametrize-collapses the three shared-shape new-clause checks
    # into one AT per the max-density mandate.
    Examples: the three mode/resume/AT-set skills
      | skill                              |
      | the nw-fast-forward skill          |
      | the nw-buddy-project-reading skill |
      | the nw-at-completeness-check skill |

  @slice-13 @driving_port @contract-shape:unbounded-preservation
  Scenario: Every roadmap mention in the buddy reading skill is classic-scoped
    When the nw-buddy-project-reading skill is read for the atdd_pure workflow
    Then every roadmap line in the nw-buddy-project-reading skill is classic-scoped

    # MODE-SCOPED clause (slice-09 / slice-10 semantic-role pattern). The
    # roadmap.json token legitimately REMAINS in the file for the classic
    # DELIVER path -- a bare-token absence assertion would be wrong. The
    # contract is the falsifiable positive predicate "every roadmap.json line
    # co-occurs with a classic / workflow.mode qualifier". NON-VACUOUS: master
    # L92 carries an unscoped roadmap.json mention
    # ("docs/feature/{id}/deliver/roadmap.json" in the wave-progress table),
    # so this scenario genuinely FAILS on master and PASSES once slice-13
    # scopes the prose. This is the ONLY non-vacuous mode-scope clause in
    # slice-13 -- the nw-fast-forward mode-scope clause from the design note
    # is vacuous (0 roadmap/log lines on master) and is not shipped.
