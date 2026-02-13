Feature: Documentation Accuracy
  As a new nWave user
  I want the installation documentation to be accurate
  So that I can successfully install nWave on a fresh machine

  Background:
    Given the installation guide exists at docs/guides/installation-guide.md

  # ==========================================================================
  # AC-10: Documentation Accuracy
  # ==========================================================================

  @ac10 @manual
  Scenario: Quick start commands work on virgin machine
    Given I have a fresh machine with Python installed
    And pipx is installed via "pip install pipx"
    When I follow the quick start instructions:
      | step | command            |
      | 1    | pipx install nwave-ai |
      | 2    | nwave-ai install      |
    Then each command should succeed
    And nWave should be installed successfully

  @ac10
  Scenario: Prerequisites are correctly stated
    Given I read the installation guide prerequisites
    Then the prerequisites should include "Python 3.10"
    And the prerequisites should include "pipx"
    And the prerequisites should NOT state "Python 3.11" as minimum

  @ac10
  Scenario: Quick start section includes virtual environment setup
    Given I read the quick start section
    Then the quick start should include "pipx install nwave-ai"
    And the quick start should include "nwave-ai install"

  @ac10
  Scenario: Documentation mentions pipx requirement
    Given I read the installation guide
    Then the guide should mention pipx is recommended
    And the guide should explain how to install pipx
    And the guide should show pipx commands for installation

  @ac10
  Scenario: Troubleshooting section addresses common errors
    Given I read the troubleshooting section
    Then the section should address "Agents Not Appearing"
    And the section should address "Installation Failed"
    And each error should have a solution with actionable commands
