Feature: Pre-flight Environment Checks
  As an nWave installer user
  I want the installer to validate my environment before attempting installation
  So that I receive clear guidance when my environment is misconfigured

  Background:
    Given the nWave installer script exists at scripts/install/install_nwave.py

  # ==========================================================================
  # AC-01: Pre-flight Environment Check Runs First
  # ==========================================================================

  @skip @ac01
  Scenario: Environment validation runs before any installation action
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the pre-flight check should pass
    And the build phase should begin
    And the installation log should contain "Pre-flight checks passed"

  @skip @ac01
  Scenario: Pre-flight check validates virtual environment first
    Given I am NOT inside a virtual environment
    When I run the nWave installer
    Then the installation should be blocked
    And no build artifacts should be created
    And the error should appear before any build output

  @skip @ac01
  Scenario: Pre-flight results are logged
    Given I am inside a virtual environment
    And pipenv is installed
    When I run the nWave installer
    Then the installation log should contain timestamp entries
    And the log should record each pre-flight check result

  # ==========================================================================
  # AC-02: Virtual Environment Hard Block
  # ==========================================================================

  @skip @ac02 @requires_no_venv
  Scenario: Installation blocked when not in virtual environment
    Given I am NOT inside a virtual environment
    When I run the nWave installer
    Then the exit code should be 1
    And the error output should contain "Virtual environment required"
    And the error output should contain "pipenv shell"
    And no installation files should be created

  @skip @ac02 @requires_no_venv
  Scenario: Skip-checks flag does not bypass virtual environment requirement
    Given I am NOT inside a virtual environment
    When I run the nWave installer with "--skip-checks" flag
    Then the exit code should be 1
    And the error output should contain "Virtual environment required"
    And the output should contain "Virtual environment check cannot be skipped"

  @skip @ac02 @requires_venv
  Scenario: Installation proceeds when in virtual environment
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the exit code should be 0
    And the output should contain "nWave Framework installed successfully"

  # ==========================================================================
  # AC-03: Pipenv-Only Enforcement
  # ==========================================================================

  @skip @ac03 @requires_venv
  Scenario: Error when pipenv is not installed
    Given I am inside a virtual environment
    And pipenv is NOT installed
    When I run the nWave installer
    Then the exit code should be 1
    And the error output should contain "pipenv is required"
    And the error output should NOT contain "pip install"
    And the error output should NOT contain "poetry"

  @skip @ac03 @requires_venv
  Scenario: Error messages reference only pipenv for dependency installation
    Given I am inside a virtual environment
    And pipenv is installed
    And the dependency "pyyaml" is missing
    When I run the nWave installer
    Then the error output should contain "pipenv install"
    And the error output should NOT contain "pip install pyyaml"
    And the error output should NOT contain "poetry add"

  @skip @ac03 @requires_venv
  Scenario: Pipenv installation guidance is actionable
    Given I am inside a virtual environment
    And pipenv is NOT installed
    When I run the nWave installer
    Then the error output should contain "[FIX]"
    And the error output should contain "pip install pipenv"
    And the error output should contain "[THEN]"
    And the error output should contain "pipenv install"
