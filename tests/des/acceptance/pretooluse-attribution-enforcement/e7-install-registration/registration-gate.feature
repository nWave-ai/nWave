# E7 — the attribution.enabled registration gate (ADR-CA-006 D7/O-4).
#
# attribution.enabled is now LOAD-BEARING again: it gates whether the
# commit-attribution hook entry is registered. Install honours the operator's
# choice; the CLI toggles the entry on and off after install. Every scenario
# asserts the settings.json hooks.PreToolUse CONTENT and the coexistence of the
# existing DES Bash guard.
#
# Driving ports: the install plugin lifecycle AND the `attribution on|off` CLI.

@driving_port @real-io @contract-shape:bounded-change
Feature: The attribution preference gates the commit-attribution hook registration

  Background:
    Given a sandboxed nWave home where the commit guard is already registered

  Scenario: A fresh install with attribution disabled registers no commit-attribution hook
    Given the operator has chosen to disable attribution
    When nWave is installed
    Then no commit-attribution hook is registered
    And the existing commit guard is still registered

  Scenario: Enabling attribution after install registers the commit-attribution hook
    Given nWave is installed with attribution disabled
    When the operator turns attribution on
    Then the commit-attribution hook is registered for Bash commands
    And the existing commit guard is still registered

  Scenario: Disabling attribution removes only the commit-attribution hook
    Given nWave is installed with attribution enabled
    When the operator turns attribution off
    Then no commit-attribution hook is registered
    And the existing commit guard is still registered

  Scenario: Re-enabling attribution never registers a duplicate commit-attribution hook
    Given nWave is installed with attribution enabled
    When the operator turns attribution on again
    Then exactly one commit-attribution hook is registered

  Scenario: Re-running the install never registers a duplicate commit-attribution hook
    Given nWave is installed with attribution enabled
    When nWave is installed again
    Then exactly one commit-attribution hook is registered
    And the existing commit guard is still registered

  Scenario: Uninstalling nWave removes the commit-attribution hook
    Given nWave is installed with attribution enabled
    When nWave is uninstalled
    Then no commit-attribution hook is registered
