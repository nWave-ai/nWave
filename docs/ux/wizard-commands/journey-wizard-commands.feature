Feature: /nw:new -- Start a new feature with guided questions

  As a developer using nWave
  I want a guided entry point that asks me what I want to build
  So that I reach the right wave command without memorizing the pipeline

  Background:
    Given the nWave framework is installed with all wave commands available

  # --- Happy Path ---

  Scenario: Greenfield feature with unclear requirements starts at DISCOVER
    Given Kenji Nakamura has no prior nWave artifacts under docs/feature/
    When Kenji types "/nw:new"
    And Kenji describes "Build a customer feedback portal"
    And Kenji indicates he has not validated the problem space yet
    Then the wizard classifies the feature as "user-facing"
    And the wizard detects greenfield state (no prior artifacts)
    And the wizard recommends starting at DISCOVER wave
    And the wizard shows the rationale "Need to validate the problem space first"
    When Kenji confirms with "Y"
    Then the wizard launches "/nw:discover" with argument "customer-feedback-portal"

  Scenario: Greenfield feature with clear requirements starts at DISCUSS
    Given Sofia Reyes has no prior nWave artifacts under docs/feature/
    When Sofia types "/nw:new"
    And Sofia describes "Add rate limiting to the API gateway"
    And Sofia indicates she has clear requirements but no formal documentation
    Then the wizard classifies the feature as "backend"
    And the wizard recommends starting at DISCUSS wave
    And the wizard shows the rationale "Define user stories and acceptance criteria"
    When Sofia confirms with "Y"
    Then the wizard launches "/nw:discuss" with argument "rate-limiting"
    And the wizard passes configuration feature_type="backend" walking_skeleton="depends"

  Scenario: Feature with existing requirements starts at DESIGN
    Given Marcus Chen has requirements artifacts at docs/feature/auth-upgrade/discuss/
    When Marcus types "/nw:new"
    And Marcus describes "Upgrade authentication to OAuth2"
    Then the wizard detects existing DISCUSS artifacts for "auth-upgrade"
    And the wizard recommends starting at DESIGN wave
    When Marcus confirms with "Y"
    Then the wizard launches "/nw:design" with argument "auth-upgrade"

  # --- Error Paths ---

  Scenario: Vague description prompts for specifics
    Given Priya Sharma types "/nw:new"
    When Priya describes "Make things better"
    Then the wizard asks for specifics:
      | question                                    |
      | What system or component are you improving? |
      | What problem are you solving?               |
      | Who benefits from this change?              |
    And the wizard provides an example: "Add rate limiting to prevent API abuse"

  Scenario: Project name conflicts with existing project
    Given Tomoko Hayashi has an existing project at docs/feature/rate-limiting/
    When Tomoko types "/nw:new"
    And Tomoko describes "Add rate limiting to the payment service"
    Then the wizard detects a name conflict with "rate-limiting"
    And the wizard offers options:
      | option                                         |
      | Continue that project (/nw:continue)           |
      | Start fresh with a different name              |
      | Archive the old one and start over             |

  Scenario: User wants to skip directly to a specific wave
    Given Amir Hassan types "/nw:new"
    When Amir says "I already have requirements, just want to design"
    Then the wizard suggests "/nw:continue" to detect existing progress
    And the wizard offers the direct command "/nw:design" as an alternative


Feature: /nw:continue -- Detect current wave progress and resume

  As a developer returning to a feature after time away
  I want to see where I left off and resume automatically
  So that I spend zero time figuring out my current wave position

  Background:
    Given the nWave framework is installed with all wave commands available

  # --- Happy Path ---

  Scenario: Single project with DISCUSS complete resumes at DESIGN
    Given Elena Voronova has a project "notification-service" with:
      | wave    | status    | artifacts                                  |
      | DISCUSS | complete  | docs/feature/notification-service/discuss/requirements.md |
      | DISCUSS | complete  | docs/feature/notification-service/discuss/user-stories.md |
      | DESIGN  | not started | (no design/ directory)                   |
    When Elena types "/nw:continue"
    Then the wizard shows progress for "notification-service":
      | wave     | status      |
      | DISCOVER | skipped     |
      | DISCUSS  | complete    |
      | DESIGN   | not started |
      | DEVOP    | not started |
      | DISTILL  | not started |
      | DELIVER  | not started |
    And the wizard recommends resuming at DESIGN wave
    When Elena confirms with "Y"
    Then the wizard launches "/nw:design" with argument "notification-service"

  Scenario: DELIVER wave partially complete resumes from last step
    Given Rajesh Patel has a project "rate-limiting" with:
      | wave    | status       |
      | DISCUSS | complete     |
      | DESIGN  | complete     |
      | DEVOP   | complete     |
      | DISTILL | complete     |
      | DELIVER | in progress  |
    And the execution-log.yaml shows steps 01-01 through 02-01 as COMMIT/PASS
    And .develop-progress.json records last failure at step 02-02
    When Rajesh types "/nw:continue"
    Then the wizard shows DELIVER progress: "Steps 01-01 through 02-01 complete, next: 02-02"
    And the wizard recommends resuming DELIVER wave
    When Rajesh confirms with "Y"
    Then the wizard launches "/nw:deliver" with argument "rate-limiting"
    And the deliver command auto-resumes from step 02-02

  Scenario: Multiple active projects prompts selection
    Given Wei Zhang has two projects:
      | project             | last_wave | last_modified |
      | rate-limiting       | DESIGN    | 2026-02-20    |
      | user-notifications  | DISCUSS   | 2026-02-18    |
    When Wei types "/nw:continue"
    Then the wizard lists both projects ordered by last modification
    And asks Wei to select a project by number
    When Wei selects "1" (rate-limiting)
    Then the wizard shows progress for "rate-limiting" and recommends DESIGN

  # --- Error Paths ---

  Scenario: No active projects found
    Given Fatima Al-Rashid has no directories under docs/feature/
    When Fatima types "/nw:continue"
    Then the wizard shows "No active projects found under docs/feature/"
    And suggests running "/nw:new" to start a new feature

  Scenario: Artifacts from non-adjacent waves detected
    Given Carlos Mendez has a project "payment-gateway" with:
      | wave    | status   |
      | DISCUSS | complete |
      | DESIGN  | missing  |
      | DISTILL | missing  |
      | DELIVER | partial  |
    When Carlos types "/nw:continue"
    Then the wizard warns about skipped waves (DESIGN, DISTILL)
    And offers options:
      | option                                   |
      | Resume from DESIGN (fill the gap)        |
      | Continue DELIVER (accept current state)  |
      | Show all artifacts for manual review     |

  Scenario: Corrupted artifact detected
    Given Li Wei has a project "search-index" with:
      | artifact                                           | state          |
      | docs/feature/search-index/discuss/requirements.md  | empty (0 bytes)|
    When Li types "/nw:continue"
    Then the wizard flags "requirements.md is empty (0 bytes)"
    And recommends re-running DISCUSS wave to regenerate requirements
