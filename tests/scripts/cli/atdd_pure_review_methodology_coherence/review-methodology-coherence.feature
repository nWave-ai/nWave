@coupled:slice-10-review-methodology-coherence
Feature: The review methodology and reviewer agents document the atdd_pure roadmap-free spine

  A reviewer (or an operator running a review) on an atdd_pure feature reads
  review-methodology skills and reviewer-agent specs that describe the ADR-028
  7-phase A->G roadmap-free sibling spine and the ADR-029 PO/ATD reviewer
  DoR/DoD re-split -- never the stale "extension of ADR-025" framing, never
  "execution-log.json" presented as THE sole phase record. slice-10 ships this
  coherence prose into six files: three review-methodology skills and three
  reviewer-agent specs.

  The scenarios below form one coupled AT group
  (@coupled:slice-10-review-methodology-coherence): the six files' atdd_pure
  alignment is one indivisible coherence contract -- a review skill that names
  the roadmap-free sibling spine but a reviewer agent still rooted in
  execution-log-as-sole-phase-record would ship a half-aligned review surface.
  coupling_justification recorded in the slice plan (feature-delta slice-10
  row).

  # ADR-028 7-phase A->G sibling spine + ADR-029 reviewer re-split / slice-10
  # of the atdd-pure-roadmap-free-rollout.
  #
  # TESTABLE-SURFACE FINDING (see acceptance brief WAVE: DISTILL section).
  # slice-10's only deliverable is the atdd_pure-coherence prose edited into
  # six review-methodology / reviewer-agent files. They ship NO CLI, NO
  # main(), NO exit code; master vs post-slice-10 differ ONLY in markdown
  # text. A behavioural / regression AT is structurally impossible -- there is
  # nothing to invoke. Per the refined H3 rule a slice whose entire deliverable
  # is .md prose is Class P, gated by the executable coherence test.
  #
  # SEPARATE from slices 04 / 09 / 15 (coherence over disjoint file sets).
  # slice-10 targets six disjoint files. This .feature asserts ONLY the
  # slice-10 contract clauses.
  #
  # Driving surface: the production SKILL.md / agent .md content at its repo
  # path (read as-is, Pillar 3). Layer 3 (FS-reading coherence) -- example-
  # only, no PBT (Mandate 9/11). Two coherence mechanisms (design note
  # H2-final):
  #
  #  * REGEX mechanism -- 4 files. Each carries a present_regex token VERIFIED
  #    0 occurrences on master 2026-05-20 (the falsifiable regression signal):
  #    "roadmap-free sibling spine" (nw-review + nw-deliver-orchestration),
  #    "slice plan passes" (product-owner reviewer), "ATs ARE the acceptance
  #    criteria" (acceptance-designer reviewer). Each row FAILS on master and
  #    PASSES once slice-10 adds the prose.
  #
  #    VACUITY FLAG (acceptance brief): the four absent_regex tokens
  #    ("extension of ADR-025", "7-phase extension", "AC derived from UAT",
  #    "derived from PO Given-When-Then") ALSO match 0 lines on master -- the
  #    absent clause is non-falsifiable. It is asserted only as a documented
  #    non-regression guard; the slice-10 RED signal for every regex file is
  #    the falsifiable present predicate alone.
  #
  #  * SEMANTIC-ROLE mechanism -- 2 files (tdd-review-enforcement,
  #    software-crafter reviewer). Two falsifiable predicates: (1) the file
  #    NAMES the atdd_pure phase record "AT-completion ledger" (master-absent,
  #    0 occurrences in both files); (2) every line mentioning
  #    "execution-log.json" co-occurs with a classic / workflow.mode qualifier
  #    (master carries 3 unscoped lines in each file). NON-VACUOUS for both
  #    predicates in both files.

  Background:
    Given a review-methodology or reviewer-agent file

  @slice-10 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every regex-gated review file names the atdd_pure roadmap-free spine
    When <file> is read for the atdd_pure workflow
    Then <file> names the atdd_pure roadmap-free spine
    And the stale classic-only framing is absent from <file>

    # The four slice-10 REGEX rows, one per file. Each present_regex token is
    # verified 0 occurrences on master 2026-05-20, so each row FAILS on master
    # (the "names the atdd_pure roadmap-free spine" Then) and PASSES once
    # slice-10 adds the prose. The outline parametrize-collapses the four
    # shared-shape regex checks into one AT per the max-density mandate.
    #
    # The "stale classic-only framing is absent" And step is the documented
    # non-regression guard for the four absent_regex tokens -- it is VACUOUS
    # on master (those tokens are already absent) and is asserted as a guard,
    # not as a slice-10 RED signal. The composition flags absent_is_vacuous so
    # the guard step never masquerades as the regression signal.
    Examples: the four regex-gated review files
      | file                                    |
      | the nw-review skill                     |
      | the nw-deliver-orchestration skill      |
      | the product-owner reviewer agent        |
      | the acceptance-designer reviewer agent  |

  @slice-10 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every semantic-role-gated reviewer file names the atdd_pure phase record
    When <file> is read for the atdd_pure workflow
    Then <file> names the atdd_pure AT-completion-ledger phase record

    # SEMANTIC-ROLE predicate 1. The ledger token "AT-completion ledger" is
    # verified 0 occurrences on master in both files 2026-05-20 -- each row
    # FAILS on master and PASSES once slice-10 names the phase record. The
    # outline parametrize-collapses the two shared-shape predicate-1 checks
    # into one AT per the max-density mandate.
    Examples: the two semantic-role-gated reviewer files
      | file                                |
      | the tdd-review-enforcement skill    |
      | the software-crafter reviewer agent |

  @slice-10 @driving_port @contract-shape:unbounded-preservation
  Scenario Outline: Every execution-log mention in a reviewer file is scoped to the classic path
    When <file> is read for the atdd_pure workflow
    Then every execution-log line in <file> is classic-scoped

    # SEMANTIC-ROLE predicate 2 (the slice-10 design-note semantic-role
    # pattern). The "execution-log.json" token legitimately REMAINS in both
    # files for the classic path -- a bare-token absence assertion would be
    # wrong. The contract is the falsifiable positive predicate "every such
    # line co-occurs with a classic / workflow.mode qualifier". NON-VACUOUS:
    # master carries 3 unscoped lines in each file (tdd-review-enforcement
    # L93/L95/L260, software-crafter-reviewer L80/L86/L171), so each row
    # genuinely FAILS on master and PASSES once slice-10 scopes the prose.
    Examples: the two semantic-role-gated reviewer files
      | file                                |
      | the tdd-review-enforcement skill    |
      | the software-crafter reviewer agent |
