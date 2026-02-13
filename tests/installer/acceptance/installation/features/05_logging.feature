Feature: Installation Logging
  As an nWave installer user
  I want all installation actions and errors logged to a file
  So that I can troubleshoot issues and maintain an audit trail

  Background:
    Given the nWave installer script exists at scripts/install/install_nwave.py

  # ==========================================================================
  # AC-09: Installation Logging
  # ==========================================================================

  @skip @ac09 @requires_venv
  Scenario: Log file is created at standard location
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then a log file should exist at "~/.claude/nwave-install.log"

  @skip @ac09 @requires_venv
  Scenario: Successful actions are logged with timestamp
    Given I am inside a virtual environment
    And pipenv is installed
    And all required dependencies are present
    When I run the nWave installer
    Then the log file should contain timestamped entries
    And the log should contain "Build completed successfully"
    And the log should contain "Installation validation: PASSED"

  @skip @ac09 @requires_no_venv
  Scenario: Errors are logged with detail
    Given I am NOT inside a virtual environment
    When I run the nWave installer
    Then the log file should contain the error
    And the log should contain "Virtual environment required"
    And the log entry should include timestamp

  @skip @ac09 @requires_venv
  Scenario: Pre-flight check results are logged
    Given I am inside a virtual environment
    And pipenv is installed
    When I run the nWave installer
    Then the log should contain pre-flight check entries
    And the log should contain "virtual environment" check result
    And the log should contain "pipenv" check result

  @skip @ac09 @requires_venv
  Scenario: Log persists across installation attempts
    Given I am inside a virtual environment
    And pipenv is installed
    And a previous log file exists
    When I run the nWave installer
    Then the new log entries should be appended
    And the previous log entries should be preserved

  @skip @ac09
  Scenario: Log format is parseable
    Given an installation has been attempted
    When I examine the log file
    Then each log entry should have a consistent format
    And the format should include timestamp
    And the format should include log level
    And the format should include message
