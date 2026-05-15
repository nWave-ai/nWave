# Feature: Codex Empirical E2E Walking Skeleton
# Story: US-4 (slice-01)
# FM closed: FM-4 (test asserted internal schema instead of empirical fire)
# Strategy B: real codex binary in testcontainer, fake-codex harness fallback when binary absent
# Audit-log events: HOOK_INVOKED / HOOK_COMPLETED (per DDD-5 correction of DISCUSS AC-4.3)

Feature: Codex+DES end-to-end empirical proof
  As a developer who installed nwave-ai with --platform codex
  I want my Codex session to actually trigger DES enforcement when I run a tool
  So that I can trust the "Codex platform support" claim is empirically true

  Background:
    Given the Codex hooks schema spike artifact exists at docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md
    And the legacy test tests/e2e/test_codex_full_install.py is marked broken_schema_v0
    And the marker broken_schema_v0 is registered in pyproject.toml

  @walking_skeleton @driving_port @real-io @us-4 @slice-01
  Scenario: Developer installs nWave for Codex and a Bash invocation fires DES
    Given a clean Codex environment with no prior nWave hooks
    And the nwave-ai installer has been run with --platform codex
    When a Codex session invokes the Bash tool with command "echo hello"
    Then the DES PreToolUse hook is fired by Codex
    And the audit log contains a HOOK_INVOKED entry with handler "pre_tool_use"
    And the audit log contains a HOOK_COMPLETED entry with handler "pre_tool_use" and exit_code 0
    And both entries fall within the test window

  @walking_skeleton @driving_port @real-io @us-4 @slice-01
  Scenario: Walking skeleton falls back to fake-codex harness when real binary is unavailable
    Given a clean Codex environment with no prior nWave hooks
    And the real Codex binary is not available in the test environment
    And the nwave-ai installer has been run with --platform codex
    When the fake-codex harness loads the installed hooks file and invokes the Bash tool
    Then the harness reads the hooks file in the event-keyed schema
    And the harness invokes the DES adapter with the documented stdin envelope
    And the audit log contains a HOOK_COMPLETED entry with handler "pre_tool_use" and exit_code 0

  @us-4 @slice-01 @infrastructure-failure @error
  Scenario: Walking skeleton fails for the right reason when hooks file has the legacy broken schema
    Given a clean Codex environment with no prior nWave hooks
    And the installed hooks file is left in the legacy top-level-array schema
    When the fake-codex harness attempts to load the installed hooks file
    Then the harness reports a schema-shape error referencing the event-keyed root
    And no DES hook is fired
