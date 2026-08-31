@real-io @adapter-integration
Feature: The nWave installer wires DES enforcement into the pi agent
  As Devon installing nWave for pi
  I want the installer to place the DES extension and crafter skill into pi cleanly
  So that bare pi gains test-first enforcement, and uninstall leaves no trace

  Background:
    Given the DES Python library is installed
    And the pi DES extension template is available to the installer

  @US-1
  Scenario: Installing into a present pi config dir places the extension and manifest
    Given a pi config directory exists
    When the operator installs the pi DES target
    Then the rendered pi DES extension is present in the pi config directory
    And the extension records the resolved python interpreter and DES library path
    And an install manifest records the placed artifacts
    And no unrelated pi config files are disturbed

  @US-1 @error
  Scenario: Installing when pi is not present skips without failing
    Given no pi config directory exists
    When the operator installs the pi DES target
    Then the installation reports success
    And the operator is told the pi target was skipped because pi was not detected

  @US-1 @error
  Scenario: Installing before the DES library is present is refused with guidance
    Given a pi config directory exists
    And the DES Python library is not installed
    When the operator checks pi DES prerequisites
    Then the prerequisite check fails naming the missing DES library

  @US-1
  Scenario: Verifying a completed install confirms the placed artifacts
    Given a pi config directory exists
    And the pi DES target has been installed
    When the operator verifies the pi DES install
    Then the verification reports the extension and manifest are present

  @US-1 @error
  Scenario: Verifying before installing reports the missing extension
    Given a pi config directory exists
    When the operator verifies the pi DES install
    Then the verification reports the pi DES extension is missing

  @US-1
  Scenario: Reinstalling refreshes the extension without removing the operator's own pi files
    Given a pi config directory exists
    And the operator keeps their own file in the pi config directory
    And the pi DES target has been installed once
    When the operator installs the pi DES target again
    Then the rendered pi DES extension reflects the current template
    And the operator's own pi file is left untouched

  @US-1
  Scenario: Uninstalling removes every placed artifact and leaves the operator's files
    Given a pi config directory exists
    And the operator keeps their own file in the pi config directory
    And the pi DES target has been installed
    When the operator uninstalls the pi DES target
    Then the rendered pi DES extension is gone
    And the install manifest is gone
    And the operator's own pi file is left untouched

  @US-1 @error
  Scenario: Uninstalling when nothing was installed completes without error
    Given a pi config directory exists
    When the operator uninstalls the pi DES target
    Then the uninstallation reports success
