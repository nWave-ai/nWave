Feature: Feature-delta validation catches cross-wave drift before merge
  As Ale, the nwave maintainer authoring features through the wave methodology
  I want commit-time structural validation of feature-delta.md
  So that protocol-surface erosion and silent commitment drops are caught
  in under one second instead of two-hour RCA sessions hours later

  Background:
    Given a clean working directory with no prior nwave-ai state
    And the nwave-ai binary is on PATH

  # ------------------------------------------------------------------
  # Walking Skeleton — the dogfood (proves v1.0 catches the original
  # token-billing failure exemplar that triggered this entire epic)
  # ------------------------------------------------------------------

  @walking_skeleton @driving_adapter @real-io @adapter-integration @vendor_neutral @US-05 @AC-1
  Scenario: WS dogfood — validator catches token-billing silent erosion
    Given the token-billing failure exemplar at "runs/nwave-attempt/feature-delta.md"
    And the exemplar DISCUSS section commits to "real WSGI handler bound to /api/usage"
    And the exemplar DESIGN section weakens this to "framework-agnostic dispatcher" with no DDD ratification
    When the maintainer runs "nwave-ai validate-feature-delta runs/nwave-attempt/feature-delta.md" via subprocess
    Then the exit code is 0
    And stderr names the offender file and line of the DESIGN row
    And stderr contains the protocol surface "WSGI" as missing downstream
    And stderr suggests adding a DDR entry or restoring the commitment
    And no file outside the path argument was modified

  # ------------------------------------------------------------------
  # E1 — Section presence (US-02)
  # ------------------------------------------------------------------

  @US-02 @AC-1
  Scenario: Well-formed feature-delta passes E1 within budget
    Given a well-formed feature-delta with DISCUSS, DESIGN, and DISTILL sections
    When the maintainer runs the validator against the file
    Then the exit code is 0 within 1 second
    And the output reports E1 PASS

  @US-02 @AC-2 @error
  Scenario: Section heading typo reported with did-you-mean
    Given a feature-delta where the DISCUSS heading is typed "## Wave : DISCUSS" with an extra space
    When the maintainer runs the validator
    Then the exit code is 0
    And stderr names the file and line of the malformed heading
    And stderr suggests "## Wave: DISCUSS" as the closest valid heading

  # ------------------------------------------------------------------
  # E2 — Column presence (US-02)
  # ------------------------------------------------------------------

  @US-02 @AC-3 @error
  Scenario: Missing DDD column reported with file and line
    Given a feature-delta where the DESIGN commitments table omits the "DDD" column
    When the maintainer runs the validator
    Then the exit code is 0
    And stderr contains "missing column 'DDR'"
    And stderr names the file and line of the malformed table header

  # ------------------------------------------------------------------
  # E3 — Non-empty rows (US-03)
  # ------------------------------------------------------------------

  @US-03 @AC-1 @error
  Scenario: Empty cell in commitment row caught
    Given a feature-delta where a DESIGN row has an empty Commitment cell
    When the maintainer runs the validator
    Then the exit code is 0
    And stderr names the empty cell by row number

  # ------------------------------------------------------------------
  # E3b — Cherry-pick check (US-03)
  # ------------------------------------------------------------------

  @US-03 @AC-2
  Scenario: Full commitment inheritance passes E3b
    Given DISCUSS contains 3 commitment rows
    And DESIGN contains 3 commitment rows with identical Commitment text
    When the maintainer runs the validator
    Then the exit code is 0
    And the output reports E3b PASS

  @US-03 @AC-3 @error
  Scenario: Cherry-picked commitment blocked at commit time
    Given DISCUSS contains 3 commitment rows
    And DESIGN contains only 2 commitment rows
    And no DDD entry authorizes the removal of the third row
    When the maintainer runs the validator
    Then the exit code is 0
    And stderr names the missing commitment by Commitment-column text
    And stderr suggests "Add DDR entry OR restore row"

  @US-03 @AC-4
  Scenario: Authorized commitment removal passes E3b by ratification
    Given DISCUSS contains 3 commitment rows
    And DESIGN contains 2 commitment rows plus DDD-1 stating "drop CLI commitment because feature is API-only"
    And the DESIGN Impact column references "DDD-1"
    When the maintainer runs the validator
    Then the exit code is 0
    And the output reports E3b PASS

  # ------------------------------------------------------------------
  # E5 — Protocol-surface preservation (US-04)
  # ------------------------------------------------------------------

  @US-04 @AC-1
  Scenario: Protocol surface preserved across waves passes E5
    Given DISCUSS commits to "POST /api/usage real WSGI handler"
    And DESIGN commits to "POST /api/usage backed by Flask 3.x route"
    When the maintainer runs the validator
    Then the exit code is 0
    And the output reports E5 PASS

  @US-04 @AC-2 @error
  Scenario: CLI commitment dropped without DDD ratification fails E5
    Given DISCUSS commits to a CLI commitment "`nw login --device-trust` available"
    And DESIGN omits the CLI commitment
    And no DDD entry authorizes the removal
    When the maintainer runs the validator
    Then the exit code is 0
    And stderr names "`nw login --device-trust`" as the missing protocol surface

  @US-04 @AC-3
  Scenario: Authorized protocol downgrade passes E5 by ratification
    Given DISCUSS commits to "real WSGI handler"
    And DESIGN commits to "framework-agnostic dispatcher"
    And DDD-1 authorizes the change with reason "runtime probes confirm equivalence"
    And the DESIGN Impact column cites "DDD-1"
    When the maintainer runs the validator
    Then the exit code is 0
    And the output reports E5 PASS by ratification

  # ------------------------------------------------------------------
  # E4 v1.0 — Substantive Impact heuristic (US-09)
  # ------------------------------------------------------------------

  @US-09 @AC-1
  Scenario: Substantive Impact with consequence verb passes E4
    Given a commitment row whose Impact column reads "DDD-1 ratifies framework-agnostic relaxation"
    When the maintainer runs the validator
    Then the exit code is 0
    And the output reports E4 PASS

  @US-09 @AC-2 @error
  Scenario: Empty Impact text caught by E4
    Given a commitment row whose Impact column reads "ok"
    When the maintainer runs the validator
    Then the exit code is 0
    And stderr names the offender row

  @US-09 @AC-3
  Scenario: Word-padding bypass documented as v1.0 conceded gap
    Given a commitment row whose Impact column reads ten vacuous words with no consequence verb
    When the maintainer runs the validator
    Then E4 v1.0 passes by word-count threshold
    And the limitation is documented as closed by US-12 v1.1

  # ------------------------------------------------------------------
  # E4 v1.1 — Impact-must-cite (US-12) — closes the v1.0 gap
  # ------------------------------------------------------------------

  @US-12 @AC-1
  Scenario: DDD citation in Impact passes E4 v1.1
    Given a commitment row whose Impact column reads "DDD-1 ratifies framework-agnostic relaxation"
    When the maintainer runs the validator with rule R2 enabled
    Then the exit code is 0
    And the output reports E4 v1.1 PASS

  @US-12 @AC-2 @error
  Scenario: Word-padding without citation now blocked under R2
    Given a commitment row whose Impact column reads ten vacuous words with no DDD or row citation
    When the maintainer runs the validator with rule R2 enabled
    Then the exit code is 1
    And stderr names the offender row
    And stderr suggests citing DDR-N or row#N

  @US-12 @AC-3
  Scenario: Row citation in Impact passes E4 v1.1
    Given a commitment row whose Impact column reads "preserves DISCUSS#row3 verbatim"
    When the maintainer runs the validator with rule R2 enabled
    Then the exit code is 0
    And the output reports E4 v1.1 PASS

  # ------------------------------------------------------------------
  # R1 — Row-level pairing (US-11)
  # ------------------------------------------------------------------

  @US-11 @AC-1
  Scenario: Bijective row pairing passes E3b-row
    Given DISCUSS contains 3 commitment rows
    And DESIGN contains 3 commitment rows each with an Origin annotation citing the upstream row
    When the maintainer runs the validator with rule R1 enabled
    Then the exit code is 0
    And every upstream row has at least one downstream successor

  @US-11 @AC-2 @error
  Scenario: Partial row pairing reports orphan upstream rows
    Given DISCUSS contains 3 commitment rows
    And DESIGN contains only 1 commitment row citing "Origin: DISCUSS#row1"
    And no DDD entry authorizes removal of rows 2 or 3
    When the maintainer runs the validator with rule R1 enabled
    Then the exit code is 1
    And stderr names "DISCUSS#row2" and "DISCUSS#row3" as orphan upstream rows

  # ------------------------------------------------------------------
  # R3 — i18n config-extensible patterns (US-13, DD-A3)
  # ------------------------------------------------------------------

  @US-13 @AC-1 @real-io @adapter-integration
  Scenario: Italian protocol-verb list loads with at least three patterns
    Given the shipped Italian protocol-verb list at "nWave/data/protocol-verbs/it.txt"
    When the validator loads the Italian verb list
    Then the loaded list contains at least 3 patterns
    And the file is UTF-8 encoded without BOM

  @US-13 @AC-2 @real-io
  Scenario: Italian E5 catches drift on Italian protocol verb
    Given a feature-delta with DISCUSS commitment in Italian "L'utente fa POST su /api/usage"
    And DESIGN drops the POST commitment with no DDD ratification
    When the maintainer runs the validator with Italian patterns loaded
    Then the exit code is 1
    And stderr names "POST /api/usage" as missing

  @US-13 @AC-3 @real-io
  Scenario Outline: Header-only language stub loads to empty list
    Given the shipped <language> protocol-verb list at "nWave/data/protocol-verbs/<file>"
    When the validator loads the <language> verb list
    Then the loaded list has length 0
    And the file is UTF-8 encoded without BOM

    Examples:
      | language | file   |
      | Spanish  | es.txt |
      | French   | fr.txt |

  # ------------------------------------------------------------------
  # ReDoS adversarial — user-supplied regex constraint (ADR-01 Security)
  # ------------------------------------------------------------------

  @US-13 @AC-4 @error @security
  Scenario: User-supplied verb pattern with unbounded quantifier nesting rejected
    Given a per-repo override file containing the malicious pattern "(a+)+b"
    When the maintainer runs the validator
    Then the exit code is 70
    And stderr emits a "health.startup.refused" structured event
    And stderr names the rejected pattern

  @US-13 @AC-6 @error @security
  Scenario: Pathological catastrophic-backtracking pattern rejected at startup
    Given a per-repo override file containing the catastrophic pattern "(a*)*$"
    When the maintainer runs the validator
    Then the exit code is 70
    And stderr emits a "health.startup.refused" structured event
    And stderr names the rejected pattern

  # ------------------------------------------------------------------
  # Permission denied on output path — error path (US-10 error UX)
  # ------------------------------------------------------------------

  @US-10 @AC-4 @error
  Scenario: Read permission denied on feature-delta surfaces clean error
    Given a feature-delta whose file permissions deny read access
    When the maintainer runs the validator
    Then the exit code is 65
    And stderr names the file and "permission denied"

  # ------------------------------------------------------------------
  # Boundary — empty file (US-02 edge case)
  # ------------------------------------------------------------------

  @US-02 @AC-5 @error
  Scenario: Empty feature-delta file reported with clear remediation
    Given a feature-delta file containing no content at all
    When the maintainer runs the validator
    Then the exit code is 65
    And stderr names the file as empty
    And stderr suggests running "nwave-ai feature-delta init"

  # ------------------------------------------------------------------
  # US-15 — warn-only / enforce mode + maturity-manifest gate (DD-A2, DD-A7d)
  # ------------------------------------------------------------------

  @US-15 @AC-1
  Scenario: Default warn-only mode reports violation but exits zero
    Given a feature-delta with one E5 violation and no DDD ratification
    When the maintainer runs the validator without specifying enforcement mode
    Then the exit code is 0
    And stderr contains a warning prefix naming the violation

  @US-15 @AC-2 @error
  Scenario: Enforce mode refused when maturity manifest marks rules pending
    Given the rule maturity manifest reports "row_pairing_R1" as "pending"
    When the maintainer runs the validator with the enforce flag
    Then the exit code is 78
    And stderr contains "cannot enable --enforce: rules pending"
    And no validation runs in misconfigured mode

  @US-15 @AC-3
  Scenario: Enforce mode runs validation when manifest reports all rules stable
    Given the rule maturity manifest reports every required rule as "stable"
    And a well-formed feature-delta with no violations
    When the maintainer runs the validator with the enforce flag
    Then the exit code is 0
    And validation runs to completion

  # ------------------------------------------------------------------
  # US-INFRA-1 — schema.json single source of truth (DD-A1)
  # ------------------------------------------------------------------

  @US-INFRA-1 @AC-1 @real-io @adapter-integration
  Scenario: Schema file validates against draft-07 metaschema
    Given the shipped schema at "schemas/feature-delta-schema.json"
    When the validator loads the schema file at startup
    Then the schema validates against the JSON Schema draft-07 metaschema
    And the schema defines WaveSection, CommitmentRow, DDDEntry, and OriginAnnotation

  # ------------------------------------------------------------------
  # US-INFRA-2 — rule maturity manifest (DD-A2)
  # ------------------------------------------------------------------

  @US-INFRA-2 @AC-1 @real-io
  Scenario: Maturity manifest is consistent with rule code
    Given the rule maturity manifest at "nWave/data/feature-delta-rule-maturity.json"
    When the consistency check runs
    Then every rule reported as "stable" corresponds to a rule that returns the documented behavior
    And every rule reported as "pending" corresponds to a rule whose code path raises pending-rule

  # ------------------------------------------------------------------
  # Parse error handling — exit 65 (DD-A7d)
  # ------------------------------------------------------------------

  @US-02 @AC-4 @error @real-io @adapter-integration
  Scenario: Malformed feature-delta with nested fence yields parse error
    Given a feature-delta containing a nested fenced gherkin block inside a commitment cell
    When the maintainer runs the validator
    Then the exit code is 65
    And stderr names the parse error code "E0-NESTED-FENCE"
    And stderr names the file and line of the nested fence
