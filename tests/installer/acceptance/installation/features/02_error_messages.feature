Feature: Context-Aware Error Messages
  As an nWave installer user
  I want clear, actionable error messages appropriate to my context
  So that I can quickly resolve installation issues

  Background:
    Given the nWave installer script exists at scripts/install/install_nwave.py

  # ==========================================================================
  # AC-04: Context-Aware Terminal Errors
  # ==========================================================================

  @skip @ac04 @requires_no_venv
  Scenario: Terminal error format uses ERROR/FIX/THEN structure
    Given I am NOT inside a virtual environment
    And the output context is "terminal"
    When I run the nWave installer
    Then the error output should contain "[ERROR]"
    And the error output should contain "[FIX]"
    And the error output should contain "[THEN]"
    And the error should be human-readable

  @skip @ac04 @requires_venv
  Scenario: Missing dependency error shows module name in terminal
    Given I am inside a virtual environment
    And pipenv is installed
    And the dependency "pyyaml" is missing
    And the output context is "terminal"
    When I run the nWave installer
    Then the error output should contain "[ERROR]"
    And the error output should contain "yaml"
    And the error output should contain "[FIX]"
    And the error output should contain "pipenv install"

  @skip @ac04
  Scenario: Permission error provides clear terminal guidance
    Given I am inside a virtual environment
    And pipenv is installed
    And the target directory has insufficient permissions
    And the output context is "terminal"
    When I run the nWave installer
    Then the error output should contain "[ERROR]"
    And the error output should contain "Permission"
    And the error output should contain "[FIX]"

  # ==========================================================================
  # AC-05: Context-Aware Claude Code Errors
  # ==========================================================================

  @skip @ac05 @requires_no_venv
  Scenario: Claude Code context outputs JSON error for missing venv
    Given I am NOT inside a virtual environment
    And the output context is "claude_code"
    When I run the nWave installer
    Then the output should be valid JSON
    And the JSON should contain field "error_code" with value "ENV_NO_VENV"
    And the JSON should contain field "message"
    And the JSON should contain field "remediation"
    And the JSON should contain field "recoverable" with value "true"

  @skip @ac05 @requires_venv
  Scenario: Claude Code context outputs JSON error for missing pipenv
    Given I am inside a virtual environment
    And pipenv is NOT installed
    And the output context is "claude_code"
    When I run the nWave installer
    Then the output should be valid JSON
    And the JSON should contain field "error_code" with value "ENV_NO_PIPENV"
    And the JSON should contain field "message" containing "pipenv"
    And the JSON should contain field "remediation"

  @skip @ac05 @requires_venv
  Scenario: Claude Code context outputs JSON error for missing dependency
    Given I am inside a virtual environment
    And pipenv is installed
    And the dependency "pyyaml" is missing
    And the output context is "claude_code"
    When I run the nWave installer
    Then the output should be valid JSON
    And the JSON should contain field "error_code" with value "DEP_MISSING"
    And the JSON should contain field "missing_modules" as array
    And the JSON "missing_modules" array should contain "yaml"

  @skip @ac05
  Scenario: Claude Code JSON includes all required error fields
    Given I am inside a virtual environment
    And the build phase fails
    And the output context is "claude_code"
    When I run the nWave installer
    Then the output should be valid JSON
    And the JSON should contain field "error_code"
    And the JSON should contain field "message"
    And the JSON should contain field "remediation"
    And the JSON should contain field "recoverable"
    And the JSON should contain field "timestamp"

  @skip @ac05
  Scenario: Error code mapping is consistent
    Given the following error conditions and expected codes:
      | condition              | error_code      |
      | no virtual environment | ENV_NO_VENV     |
      | no pipenv installed    | ENV_NO_PIPENV   |
      | missing dependency     | DEP_MISSING     |
      | build failure          | BUILD_FAILED    |
      | verification failure   | VERIFY_FAILED   |
    Then each condition should produce the expected error code
