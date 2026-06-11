# Feature: Release Pipeline Extension
# Based on: architecture-design.md - Roadmap Step 02-01
# Acceptance Criteria:
#   - Plugin builds automatically on release tag
#   - Plugin zip attached as GitHub Release asset on nwave-ai/nwave
#   - Marketplace manifest generated for self-hosted marketplace
# Date: 2026-02-27

Feature: Release Pipeline Extension
  As a project maintainer
  I want the release pipeline to build and publish the plugin automatically
  So that every nWave release is available as a plugin without manual steps

  Background:
    Given the nWave source tree is available
    And a clean output directory for the plugin build
    And default build configuration for the nWave source tree

  # --- Happy Path: Automated Build ---

  Scenario: Plugin build integrates into existing release workflow
    Given a release tag "v2.18.0" is created
    When the release pipeline runs the plugin build step
    Then the plugin directory is generated with version "2.18.0"
    And the plugin build step runs after the existing distribution build

  Scenario: Plugin version matches the release version
    Given a release tag "v2.18.1" is created
    When the release pipeline runs the plugin build step
    Then the plugin metadata version is "2.18.1"

  # --- Happy Path: Distribution ---

  Scenario: Plugin directory is ready for repository publication
    When the plugin assembler builds the plugin
    Then the plugin directory can be committed as a standalone repository
    And the plugin directory does not contain development-only files

  Scenario: Marketplace manifest is generated for self-hosted distribution
    When the plugin assembler builds the plugin
    Then the marketplace manifest contains the plugin name and version
    And the marketplace manifest contains a download reference

  # --- Error Paths ---

  Scenario: Release pipeline fails gracefully when plugin build fails
    Given the source tree is missing the agents directory
    When the release pipeline runs the plugin build step
    Then the plugin build step reports failure
    And the existing release artifacts are not affected

  # --- Edge Cases ---

  Scenario: Plugin build is idempotent across repeated runs
    When the plugin assembler builds the plugin twice with the same configuration
    Then both builds produce identical plugin directories
