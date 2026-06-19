# Feature: Milestone 1 - Collision-Free Skills
# Based on: story-map.md Release 1 (~94 unique skills, ~13 agents fully migrated)
# Stories covered: US-03, US-05, US-06 (non-colliding subset)
# Date: 2026-03-14

Feature: Collision-Free Skill Installation
  As a framework maintainer
  I want all non-colliding skills installed to the auto-loading path
  So that agents with unique skill names start with skills injected automatically

  Background:
    Given the nWave source tree contains skill directories
    And the installer plugin is available

  # --- US-03: Source Structure Validation ---

  Scenario: All non-colliding skills exist in nw-prefixed directory format
    Given the source tree has been restructured
    When the skill directories are scanned
    Then each non-colliding skill has a directory named "nw-{skill-name}"
    And each directory contains exactly one file named SKILL.md
    And no files remain in old agent-grouped directories

  Scenario: Skill content is preserved after restructuring
    Given a skill file had specific content before restructuring
    When the restructured SKILL.md is read
    Then the content is identical to the original file

  # --- US-06: Installer Plugin - Clean Install ---

  Scenario: Skills plugin installs all collision-free skills
    Given the source tree has 94 non-colliding skills in nw-prefixed directories
    And a clean installation directory exists
    When the skills plugin installs all skills
    Then 94 nw-prefixed skill directories exist in the installation target
    And each installed directory contains a SKILL.md file
    And no "nw/" namespace directory exists in the installation target

  Scenario: Installation reports correct file count
    Given the source tree has skills in nw-prefixed directories
    And a clean installation directory exists
    When the skills plugin installs all skills
    Then the success message reports the number of files installed
    And the count matches the number of source skill directories

  # --- US-06: Installer Plugin - Upgrade ---

  Scenario: Old namespace directory removed during upgrade installation
    Given the user has skills at the old path "nw/software-crafter/tdd-methodology.md"
    And a clean installation directory exists
    When the skills plugin installs all skills
    Then the old "nw/" directory is completely removed
    And "nw-tdd-methodology/SKILL.md" exists in the new location

  Scenario: Upgrade replaces all old skills with new layout
    Given the user has 50 skills in the old "nw/" namespace layout
    And the source tree has skills in nw-prefixed directories
    And a clean installation directory exists
    When the skills plugin installs all skills
    Then the old "nw/" directory no longer exists
    And all source skills are installed in nw-prefixed directories

  # --- US-06: Installer Plugin - Verification ---

  Scenario: Verification passes when all skills are installed correctly
    Given all skills have been installed successfully
    When the skills plugin runs verification
    Then verification reports success
    And the verified count matches the expected skill count

  Scenario: Verification detects missing skill directories
    Given the installation is missing 3 skill directories
    When the skills plugin runs verification
    Then verification reports failure
    And the missing skill names are identified in the error

  # --- US-05: Skill Loading Path Update ---

  Scenario: Agent Skill Loading sections reference new nw-prefixed Read paths
    Given the agent definitions have Skill Loading sections
    When an agent file is read
    Then all Read paths use "~/.claude/skills/nw-{skill}/SKILL.md" format
    And no paths use old "~/.claude/skills/nw/{agent}/{skill}.md" format

  # --- Error Paths ---

  Scenario: Installation fails gracefully when source directory is missing
    Given no skills source directory exists
    And a clean installation directory exists
    When the skills plugin attempts to install skills
    Then the installation reports that no skills were found
    And no directories are created in the installation target

  Scenario: Installation handles read-only target directory
    # The "is read-only" step chmod 444's the target, populates the source so
    # the install attempts a real write, then probes whether chmod actually
    # blocks writes — skipping (pytest.skip) only where it does not (CI as
    # root). Note: on Python 3.14 chmod DOES block; the prior flake was that
    # Path.exists() stopped raising PermissionError there, so an empty-source
    # install reported success. A populated source + an explicit writability
    # guard in the plugin make the refusal deterministic across 3.10–3.14.
    Given the installation target directory is read-only
    When the skills plugin attempts to install skills
    Then the installation fails with a clear error message
    And the error identifies the permission problem

  Scenario: Verification handles missing target directory
    Given the installation target directory does not exist
    When the skills plugin runs verification
    Then verification reports failure
    And the error indicates the target directory was not found
