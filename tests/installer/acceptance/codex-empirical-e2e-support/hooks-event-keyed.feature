# Feature: Codex hooks.json conforms to event-keyed schema
# Story: US-1 (slice-02)
# FM closed: FM-1 (plugin wrote top-level array; Codex expects event-keyed object root)
# Source of truth: developers.openai.com/codex/hooks (cited at DESIGN DDD-1, confirmed by DDD-8 spike)

Feature: Codex hooks file uses event-keyed object root
  As a developer using nwave-ai with --platform codex
  I want the installed hooks file to match the schema Codex actually consumes
  So that DES hooks are loaded by Codex instead of silently ignored

  Background:
    Given a clean Codex environment with no prior nWave hooks

  @us-1 @slice-02 @driving_port @real-io
  Scenario: Install writes hooks file with event-keyed object root
    When the nwave-ai installer is run with --platform codex
    Then the installed hooks file root is an object, not an array
    And the object has a "hooks" property
    And the "hooks.PreToolUse" property is a non-empty list

  @us-1 @slice-02 @driving_port @real-io
  Scenario: Installed PreToolUse entry carries a non-empty command
    When the nwave-ai installer is run with --platform codex
    Then the PreToolUse entry exposes a non-empty command string
    And the command string references the DES hook adapter

  @us-1 @slice-02 @driving_port @real-io @property
  Scenario: Reinstalling the plugin is idempotent
    Given the nwave-ai installer has been run with --platform codex once
    When the nwave-ai installer is run with --platform codex a second time
    Then the count of nWave PreToolUse entries is identical to the first run
    And no entry is duplicated

  @us-1 @slice-02 @infrastructure-failure @error
  Scenario: Pre-existing legacy top-level-array hooks file is rejected or migrated
    Given a legacy hooks file already exists as a top-level array at the Codex hooks path
    When the nwave-ai installer is run with --platform codex
    Then the installer either migrates the file to the event-keyed schema or refuses to overwrite
    And the resulting file is never left as a top-level array

  @us-1 @slice-02 @infrastructure-failure @error
  Scenario: Pre-existing user hooks at other events are preserved
    Given a user-authored hooks file exists with a PostToolUse entry the user owns
    When the nwave-ai installer is run with --platform codex
    Then the user's PostToolUse entry remains intact
    And a PreToolUse entry is added without disturbing other event keys

  @us-1 @slice-02 @infrastructure-failure @error
  Scenario: Hooks file with malformed JSON triggers a clear installer error
    Given a hooks file already exists at the Codex hooks path containing malformed JSON
    When the nwave-ai installer is run with --platform codex
    Then the installer either rebuilds the file from scratch or reports a parse error
    And the installer does not leave the malformed bytes in place silently
