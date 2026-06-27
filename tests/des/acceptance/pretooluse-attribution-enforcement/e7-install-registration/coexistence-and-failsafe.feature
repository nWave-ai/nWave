# E7 — coexistence preservation + fail-safe registration (ADR-CA-006/CA-007; Q5
# from the prior soft-attribution feature: skip when ~/.claude is absent).
#
# Registration must NEVER stomp a neighbour: it appends to hooks.PreToolUse,
# preserving the operator's own hooks and the DES guards. When the Claude
# config is absent or corrupt, registration skips silently (registers no hook,
# leaves the file untouched) rather than crashing the install. Under ADR-CA-007
# the settings.json credit write is retired, so an absent/corrupt config simply
# leaves no attribution hook registered; the install still succeeds.
#
# Driving port: the install plugin lifecycle over a sandboxed ~/.claude.

@driving_port @real-io @contract-shape:bounded-change
Feature: Registering the commit-attribution hook preserves neighbours and fails safe

  Scenario: A hook the operator added themselves survives registration
    Given a sandboxed nWave home where the commit guard is already registered
    And the operator has added their own Bash hook
    And the operator has chosen to enable attribution
    When nWave is installed
    Then the operator's own Bash hook is still registered
    And the commit-attribution hook is registered for Bash commands

  Scenario: Registration skips when the Claude config is absent
    Given a sandboxed nWave home with no Claude configuration
    And the operator has chosen to enable attribution
    When nWave is installed
    Then no commit-attribution hook is registered
    And the install still succeeds

  Scenario: Registration warns and skips when the settings file is unreadable
    Given a sandboxed nWave home whose settings are corrupt
    And the operator has chosen to enable attribution
    When nWave is installed
    Then the corrupt settings are left untouched
    And the install still succeeds
