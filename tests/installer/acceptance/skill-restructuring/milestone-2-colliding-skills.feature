# Feature: Milestone 2 - Colliding Skills Resolution
# Based on: story-map.md Release 2 (15 colliding skills, naming convention)
# Stories covered: US-01, US-02, US-04
# Date: 2026-03-14

Feature: Colliding Skill Name Resolution
  As a framework maintainer
  I want colliding skill names resolved with unique prefixed names
  So that all agents receive their agent-specific skill content

  Background:
    Given the nWave source tree contains skill directories
    And the installer plugin is available

  # --- US-01: Audit and Collision Detection ---

  Scenario: Audit identifies all naming collisions
    Given the source tree contains skills from multiple agent groups
    When the skill audit is performed
    Then "critique-dimensions" is flagged as colliding across 7 groups
    And "review-dimensions" is flagged as colliding across 2 groups
    And "review-criteria" is flagged as colliding across 7 groups
    And no other collisions exist

  Scenario: Audit counts all skill files
    Given the source tree is fully populated
    When the skill audit is performed
    Then exactly 109 skill files are cataloged
    And all agent-to-skill references are mapped

  Scenario: Audit detects cross-agent skill references
    Given the functional software crafter references skills from the software crafter
    When the skill audit maps cross-agent references
    Then the cross-references are identified with source and target agents

  Scenario: Audit flags orphan skills with no agent reference
    Given a skill file exists that no agent references in its frontmatter
    When the skill audit checks for orphans
    Then the orphan skill is reported with its file path

  # --- US-02: Naming Convention ---

  Scenario: Colliding skills receive agent-abbreviation prefix
    Given "critique-dimensions" exists in the acceptance-designer group
    And "critique-dimensions" exists in the solution-architect group
    When the naming convention is applied
    Then the acceptance-designer variant becomes "nw-ad-critique-dimensions"
    And the solution-architect variant becomes "nw-sa-critique-dimensions"
    And both names are unique

  Scenario: All 16 colliding skills receive unique names
    Given 16 skill files share names across agent groups
    When the naming convention is applied to all collisions
    Then 16 unique nw-prefixed directory names are produced
    And each name contains the original skill name as a suffix
    And no two names are identical

  Scenario: Non-colliding skills retain simple nw-prefix
    Given "tdd-methodology" exists only in the software-crafter group
    When the naming convention is applied
    Then the directory name is "nw-tdd-methodology"
    And no agent abbreviation is included

  @property
  Scenario: All 109 target directory names are unique
    Given the naming convention has been applied to all 109 skills
    When uniqueness is validated across all target names
    Then zero duplicate directory names exist

  @property
  Scenario: Every skill directory name starts with nw-prefix
    Given the naming convention has been applied to all skills
    When the directory names are inspected
    Then every directory name starts with "nw-"

  # --- US-04: Agent Frontmatter Updates ---

  Scenario: Renamed skill reference updated in agent frontmatter
    Given the acceptance-designer agent previously listed "critique-dimensions"
    And the directory was renamed to "nw-ad-critique-dimensions"
    When the agent frontmatter is updated
    Then the skills list contains "nw-ad-critique-dimensions"
    And "critique-dimensions" no longer appears in the skills list

  Scenario: Non-colliding skill references remain unchanged
    Given the troubleshooter agent lists "nw-five-whys-methodology"
    When the agent frontmatter is validated
    Then "nw-five-whys-methodology" remains in the skills list

  Scenario: All frontmatter skill references resolve to existing directories
    Given all agent definitions have been updated
    When every skill reference is checked against the source tree
    Then every skill name has a matching directory
    And zero dangling references exist

  # --- Error Paths ---

  Scenario: Naming convention rejects abbreviation collision
    Given two agents produce the same abbreviation
    When the naming convention detects the abbreviation collision
    Then the convention falls back to the full agent name prefix
    And the resulting names remain unique

  Scenario: Audit reports content difference for same-named skills
    Given two skills share the name "critique-dimensions"
    And their content differs
    When the audit compares content hashes
    Then the collision is marked as requiring separate directories
