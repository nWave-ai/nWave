Feature: Post-Installation Verification
  As an nWave installer user
  I want automatic verification after installation and a standalone verification command
  So that I can confirm my installation is complete and correct

  Background:
    Given the nWave installer script exists at scripts/install/install_nwave.py

  # ==========================================================================
  # AC-07: Automatic Post-Installation Verification
  # ==========================================================================

  @skip @ac07 @requires_venv
  Scenario: Verification runs after successful build
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the output should contain "Validating installation"
    And the verification should run automatically
    And the output should contain "Installation validation: PASSED"

  @skip @ac07 @requires_venv
  Scenario: Verification reports agent file count
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the output should contain "Agents installed:"
    And the agent count should be reported
    And the agent count should be at least 10

  @skip @ac07 @requires_venv
  Scenario: Verification reports command file count
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the output should contain "Commands installed:"
    And the command count should be reported

  @skip @ac07 @requires_venv
  Scenario: Verification reports manifest existence
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the output should contain "Installation manifest created"
    And the manifest file should exist at "~/.claude/nwave-manifest.txt"

  @skip @ac07
  Scenario: Verification detects missing essential files
    Given a partial installation exists
    And the essential command "discuss.md" is missing
    When I run the verification
    Then the verification should fail
    And the error should list "discuss.md" as missing

  # ==========================================================================
  # AC-08: Standalone Verification Command
  # ==========================================================================

  @skip @ac08
  Scenario: Standalone verification script exists
    Given the verification script should exist at scripts/install/verify_nwave.py
    When I check for the verification script
    Then the script should be present
    And the script should be executable

  @skip @ac08 @requires_venv
  Scenario: Verification passes when fully installed
    Given nWave is fully installed
    And all agent files are present
    And all command files are present
    And the manifest file exists
    When I run the standalone verification script
    Then the exit code should be 0
    And the output should contain "Verification: PASSED"
    And the output should list installed components

  @skip @ac08
  Scenario: Verification fails with remediation when files missing
    Given a partial installation exists
    And the agent file "business-analyst.md" is missing
    When I run the standalone verification script
    Then the exit code should be 1
    And the output should contain "Verification: FAILED"
    And the output should contain "business-analyst.md"
    And the output should contain "[FIX]"
    And the output should contain "reinstall"

  @skip @ac08
  Scenario: Verification checks essential DW commands
    Given a partial installation exists
    When I run the standalone verification script
    Then the verification should check for essential commands:
      | command   |
      | discuss   |
      | design    |
      | distill   |
      | develop   |
      | deliver   |
    And missing commands should be reported

  @skip @ac08
  Scenario: Verification validates schema template
    Given a partial installation exists
    And the schema template is missing
    When I run the standalone verification script
    Then the verification should fail
    And the error should mention "schema template"
    And the error should provide remediation guidance
