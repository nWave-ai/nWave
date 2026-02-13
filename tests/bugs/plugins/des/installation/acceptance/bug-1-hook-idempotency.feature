# Feature: Hook Installation Idempotency Bug Detection
# Bug: Running installer multiple times creates duplicate hook entries
# Evidence: settings.local.json shows duplicate PreToolUse and SubagentStop hooks
# Root Cause: _is_des_hook() check may not properly detect existing hooks
# Date: 2026-02-04

Feature: Hook Installation Idempotency
  As a developer
  I want DES hooks to be installed exactly once
  So that settings.local.json remains clean and uninstall works correctly

  Background:
    Given the test environment is initialized
    And a temporary Claude config directory exists

  # ============================================================================
  # BUG DETECTION SCENARIOS - These tests FAIL with current buggy code
  # When bugs are fixed, these tests will PASS
  # ============================================================================

  @bug-1 @priority-critical
  Scenario: Multiple installs should not duplicate hooks
    # Current Behavior (BUG): After 2 installs, settings.local.json contains
    # 2 identical PreToolUse hooks and 2 identical SubagentStop hooks
    # Expected Behavior: Exactly 1 hook of each type regardless of install count

    Given a clean settings.local.json with no hooks
    When I install DES hooks
    And I install DES hooks again
    Then settings.local.json should contain exactly 3 PreToolUse hook
    And settings.local.json should contain exactly 1 SubagentStop hook
    And no duplicate hook entries should exist

  @bug-1 @priority-critical
  Scenario: Uninstall should remove all DES hooks including duplicates
    # Current Behavior (BUG): Uninstall may not remove all duplicate instances
    # if multiple install runs created duplicates
    # Expected Behavior: Uninstall removes ALL DES hooks, restoring clean state

    Given settings.local.json contains 2 duplicate DES PreToolUse hooks
    And settings.local.json contains 2 duplicate DES SubagentStop hooks
    When I uninstall DES hooks
    Then settings.local.json should contain 0 DES PreToolUse hooks
    And settings.local.json should contain 0 DES SubagentStop hooks
    And non-DES hooks should be preserved

  @bug-1 @priority-high
  Scenario: Install after uninstall should work cleanly
    # Validates that the install->uninstall->install cycle works correctly
    # without accumulating duplicate entries

    Given DES hooks were previously installed and uninstalled
    When I install DES hooks
    Then settings.local.json should contain exactly 3 PreToolUse hook
    And settings.local.json should contain exactly 1 SubagentStop hook

  @bug-1 @failing @priority-high
  Scenario: Hook detection works for both old and new command formats
    # The _is_des_hook() method must detect both formats:
    # - Old: python3 src/des/.../claude_code_hook_adapter.py
    # - New: python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter
    # Bug: Detection may miss one format, causing duplicates

    Given settings.local.json contains a DES hook with old format command
    When I check if DES hooks are already installed
    Then the hook detection should return True
    And installing hooks again should not add duplicates

  @bug-1 @priority-high
  Scenario: Mixed format hooks should not cause duplicates
    # Edge case: If settings.local.json has old format and we install new format,
    # both might coexist as duplicates

    Given settings.local.json contains a DES hook with old format command
    When I install DES hooks using new format
    Then settings.local.json should contain exactly 3 PreToolUse hook
    And the hook should use the new command format

  @bug-1 @priority-medium
  Scenario: Preserving non-DES hooks during install
    # Regression test: Ensure other hooks are not affected by DES installation

    Given settings.local.json contains a custom non-DES PreToolUse hook
    When I install DES hooks
    Then the custom non-DES hook should still exist
    And settings.local.json should contain exactly 3 DES PreToolUse hook
    And settings.local.json should contain the custom non-DES hook

  @bug-1 @priority-medium
  Scenario: Preserving non-DES hooks during uninstall
    # Regression test: Ensure uninstall only removes DES hooks

    Given settings.local.json contains a custom non-DES PreToolUse hook
    And settings.local.json contains DES hooks
    When I uninstall DES hooks
    Then the custom non-DES hook should still exist
    And settings.local.json should contain 0 DES hooks
