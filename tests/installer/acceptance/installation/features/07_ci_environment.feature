Feature: CI Environment Detection
  As an nWave installer user
  I want the installer to detect CI/CD environments automatically
  So that output is optimized for CI logs and non-interactive execution

  Background:
    Given the nWave installer script exists at scripts/install/install_nwave.py

  # ==========================================================================
  # AC-11: CI Environment Detection
  # ==========================================================================

  @skip @ac11
  Scenario: CI detection via GITHUB_ACTIONS environment variable
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment variable "GITHUB_ACTIONS" is set to "true"
    When I run the nWave installer
    Then CI mode should be detected
    And the output should indicate "GitHub Actions" environment

  @skip @ac11
  Scenario: CI detection via GITLAB_CI environment variable
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment variable "GITLAB_CI" is set to "true"
    When I run the nWave installer
    Then CI mode should be detected
    And the output should indicate "GitLab CI" environment

  @skip @ac11
  Scenario: CI detection via generic CI environment variable
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment variable "CI" is set to "true"
    When I run the nWave installer
    Then CI mode should be detected
    And the output should indicate "Generic CI" environment

  @skip @ac11
  Scenario: CI detection via JENKINS_URL environment variable
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment variable "JENKINS_URL" is set to "http://jenkins.local"
    When I run the nWave installer
    Then CI mode should be detected
    And the output should indicate "Jenkins" environment

  # ==========================================================================
  # AC-12: CI Mode Output Behavior
  # ==========================================================================

  @skip @ac12
  Scenario: CI mode disables ANSI color codes in output
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment is detected as CI
    When I run the nWave installer
    Then the output should NOT contain ANSI escape codes
    And the output should be plain text without formatting

  @skip @ac12
  Scenario: CI mode enables verbose output by default
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment is detected as CI
    When I run the nWave installer with default settings
    Then the output should include detailed progress information
    And each installation step should be logged

  @skip @ac12
  Scenario: CI mode disables interactive prompts
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment is detected as CI
    When the installer would normally prompt for confirmation
    Then no interactive prompt should appear
    And the installer should proceed with default behavior

  # ==========================================================================
  # AC-13: CI Exit Codes
  # ==========================================================================

  @skip @ac13
  Scenario: CI mode returns non-zero exit code on failure
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment is detected as CI
    And a required dependency is missing
    When I run the nWave installer
    Then the exit code should be 1
    And failure details should be in stdout for CI log capture

  @skip @ac13
  Scenario: CI mode returns zero exit code on success
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment is detected as CI
    And all required dependencies are present
    When I run the nWave installer
    Then the exit code should be 0
    And success confirmation should be in stdout

  # ==========================================================================
  # AC-14: Container Environment Detection
  # ==========================================================================

  @skip @ac14
  Scenario: Container environment triggers warning but not block
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment is detected as Docker container
    When I run the nWave installer
    Then a warning should be logged about container environment
    And the installation should continue
    And the exit code should be 0 if otherwise successful

  @skip @ac14
  Scenario: Kubernetes container environment is detected
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment variable "KUBERNETES_SERVICE_HOST" is set
    When I run the nWave installer
    Then the output should indicate container environment
    And a warning about unsupported configuration should appear
    And installation should not be blocked

  # ==========================================================================
  # AC-15: CI and Container Combined Detection
  # ==========================================================================

  @skip @ac15
  Scenario: CI inside container shows both contexts
    Given I am inside a virtual environment
    And pipenv is installed
    And the environment variable "GITHUB_ACTIONS" is set to "true"
    And the environment is detected as Docker container
    When I run the nWave installer
    Then CI mode should be detected
    And container environment should be detected
    And both contexts should be logged

  @skip @ac15
  Scenario: Non-CI non-container environment uses default behavior
    Given I am inside a virtual environment
    And pipenv is installed
    And no CI environment variables are set
    And not running in a container
    When I run the nWave installer
    Then normal terminal output mode should be used
    And color output should be allowed if terminal supports it
