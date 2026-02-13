Feature: Installer Manifest Circular Dependency Bug

  Bug Description:
    The installer has a circular dependency where the manifest is only created
    if validation passes, but validation fails if the manifest doesn't exist.

    Current broken flow:
      1. install_framework() executes successfully
      2. validate_installation() runs and checks if manifest exists
      3. Validation FAILS because manifest doesn't exist yet
      4. create_manifest() is ONLY called if validation passes
      5. Result: manifest never gets created, installation always fails

    Expected flow:
      1. install_framework() executes successfully
      2. create_manifest() executes (before validation)
      3. validate_installation() runs and finds manifest exists
      4. Validation PASSES
      5. Result: successful installation with manifest

  Background:
    Given I have a clean test environment
    And no nWave installation exists

  Scenario: Fresh installation should create manifest before validation
    Given the installer is ready to run
    When I run the nWave installer
    Then the installation should complete successfully
    And the manifest file should exist at ~/.claude/nwave-manifest.txt
    And the validation should pass
    And the installer should exit with code 0

  Scenario: Manifest creation should not depend on validation passing
    Given the installer is ready to run
    When I run the nWave installer
    Then the manifest should be created before the validation step
    And the manifest should contain installation metadata
    And the manifest should list installed components

  Scenario: Validation should check existing manifest not create it
    Given the installer is ready to run
    When I run the nWave installer
    Then the manifest should be created before the validation step
    And the validation should find the existing manifest
    And the validation should not attempt to create the manifest
    And the validation should pass
