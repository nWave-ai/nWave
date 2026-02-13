Feature: Dependency Verification Before Build
  As an nWave installer user
  I want the installer to verify all dependencies before attempting to build
  So that I know exactly what is missing and how to fix it

  Background:
    Given the nWave installer script exists at scripts/install/install_nwave.py
    And I am inside a virtual environment
    And pipenv is installed

  # ==========================================================================
  # AC-06: Dependency Verification Before Build
  # ==========================================================================

  @skip @ac06
  Scenario: All dependencies present allows check to pass
    Given all required dependencies are present
    When I run the nWave installer
    Then the pre-flight check should pass
    And the output should contain "Dependency check: PASSED"
    And the build phase should begin

  @skip @ac06
  Scenario: Single missing dependency shows module name
    Given the dependency "pyyaml" is missing
    And the dependency "pathlib" is present
    When I run the nWave installer
    Then the exit code should be 1
    And the error output should contain "Missing required module: yaml"
    And the error output should contain "[FIX]"
    And the error output should contain "pipenv install pyyaml"

  @skip @ac06
  Scenario: Multiple missing dependencies lists all modules
    Given the dependency "pyyaml" is missing
    And the dependency "requests" is missing
    When I run the nWave installer
    Then the exit code should be 1
    And the error output should contain "yaml"
    And the error output should contain "requests"
    And the error output should contain "pipenv install"

  @skip @ac06
  Scenario: Dependency check runs before build attempt
    Given the dependency "pyyaml" is missing
    When I run the nWave installer
    Then the error should appear before any build output
    And the output should NOT contain "Building IDE bundle"
    And no build artifacts should be created

  @skip @ac06
  Scenario: Required dependencies list is comprehensive
    Given I am running a fresh installation check
    When the installer validates dependencies
    Then the following modules should be checked:
      | module   | required_for           |
      | yaml     | YAML parsing           |
      | pathlib  | Path manipulation      |
    And missing modules should be reported

  @skip @ac06
  Scenario: Dependency error provides complete remediation
    Given the dependency "pyyaml" is missing
    When I run the nWave installer
    Then the error output should contain "[ERROR]"
    And the error output should contain "Missing required module"
    And the error output should contain "[FIX]"
    And the error output should contain "pipenv install"
    And the error output should contain "[THEN]"
    And the error output should contain "run the installer again"
