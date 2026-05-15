# Feature: DES hook command invokes adapter with the documented argv token
# Story: US-2 (slice-03)
# FM closed: FM-2 (command emitted without the required pre-tool-use positional argv)
# Adapter contract source: src/des/adapters/drivers/hooks/hook_router.py (verified at DESIGN DDD-4)

Feature: Installed hook command carries the DES adapter argv contract
  As a developer using nwave-ai with --platform codex
  I want the installed hook command to invoke the DES adapter with the correct event token
  So that the adapter validates the tool event instead of exiting 1 on every fire

  Background:
    Given a clean Codex environment with no prior nWave hooks

  @us-2 @slice-03 @driving_port @real-io
  Scenario: Installed PreToolUse command ends with the pre-tool-use argv token
    When the nwave-ai installer is run with --platform codex
    Then every nWave PreToolUse command string ends with the token "pre-tool-use"
    And no command string omits the event positional argument

  @us-2 @slice-03 @driving_port @real-io
  Scenario: Hook command exits 0 on a synthetic Codex Bash tool event
    Given the nwave-ai installer has been run with --platform codex
    When the installed PreToolUse hook command is invoked with a synthetic Codex Bash tool-event stdin payload
    Then the adapter exits with status 0
    And the adapter writes at least one observable artifact

  @us-2 @slice-03 @driving_port @real-io
  Scenario: Adapter emits a HOOK_INVOKED audit entry when invoked end-to-end
    Given the nwave-ai installer has been run with --platform codex
    When the installed PreToolUse hook command is invoked with a synthetic Codex Bash tool-event stdin payload
    Then the audit log contains a HOOK_INVOKED entry with handler "pre_tool_use"
    And the audit log contains a HOOK_COMPLETED entry with handler "pre_tool_use" and exit_code 0

  @us-2 @slice-03 @infrastructure-failure @error
  Scenario: Adapter invoked without argv token surfaces the documented missing-argument error
    Given the nwave-ai installer has been run with --platform codex
    When the DES adapter entrypoint is invoked with no event positional argument
    Then the adapter exits with status 1
    And the error reason mentions "Missing command argument"

  @us-2 @slice-03 @infrastructure-failure @error
  Scenario: Adapter invoked with malformed stdin envelope handles parse failure gracefully
    Given the nwave-ai installer has been run with --platform codex
    When the installed PreToolUse hook command is invoked with malformed JSON on stdin
    Then the adapter does not raise an uncaught exception
    And the adapter emits a HOOK_PROTOCOL_ANOMALY audit entry with anomaly_type "json_parse_error"
