@attribution-activation-coupling @cli-toggle
Feature: Toggling attribution drives the hook and the preference, not the settings credit
  Turning attribution on registers the gated commit hook and records the
  preference — it never writes the retired settings credit. Turning it off
  removes only the attribution hook (leaving the execution guard intact), records
  the disabled preference, and cleans any legacy settings block. Status reports
  the effective per-repo scope.

  # AB-7 — on: hook registered, preference on, NO settings credit written.
  @ab-7 @driving_port @contract-shape:bounded-change
  Scenario: Turning attribution on registers the hook and records the preference
    Given a active repo
    And the attribution commit hook is not registered
    When the operator turns attribution on
    Then the attribution commit hook is registered
    And the attribution preference is recorded as on
    And no managed attribution credit is written to the Claude settings

  # AB-7 — idempotent: turning on twice registers exactly one hook.
  @ab-7 @contract-shape:bounded-change
  Scenario: Turning attribution on twice registers exactly one hook
    Given a active repo
    And the attribution commit hook is not registered
    When the operator turns attribution on
    And the operator turns attribution on again
    Then exactly one attribution commit hook is registered

  # AB-6 — off: attribution hook removed; execution guard intact; preference off; legacy cleaned.
  @ab-6 @driving_port @contract-shape:bounded-change
  Scenario: Turning attribution off removes only the attribution hook
    Given a active repo
    And the nWave execution guard is registered
    And the attribution commit hook is registered
    When the operator turns attribution off
    Then the attribution commit hook is not registered
    And the nWave execution guard is still registered
    And the attribution preference is recorded as off

  @ab-6 @contract-shape:bounded-change
  Scenario: Turning attribution off cleans a legacy settings credit
    Given a active repo
    And an nWave-managed legacy attribution credit in the Claude settings
    And the attribution commit hook is registered
    When the operator turns attribution off
    Then the legacy attribution credit is removed from the Claude settings

  # AB-8 — status through the real command line (driving-adapter subprocess proof).
  @ab-8 @driving_adapter @real-io @contract-shape:unbounded-preservation
  Scenario: Operator asks for status through the command line in an active repo
    Given a active repo
    And attribution preference is on
    When the operator asks for attribution status through the command line
    Then the status reports attribution is active for this repo
    And the operation completes without error

  # AB-8 — status distinguishes on+active from on+inactive (effective scope).
  @ab-8 @driving_port @contract-shape:unbounded-preservation
  Scenario: Status reports active scope in an active repo
    Given a active repo
    And attribution preference is on
    When the operator asks for attribution status
    Then the status reports attribution is active for this repo

  @ab-8 @driving_port @contract-shape:unbounded-preservation
  Scenario: Status reports inactive scope in an inactive repo
    Given a inactive repo
    And attribution preference is on
    When the operator asks for attribution status
    Then the status reports attribution is inactive for this repo

  # AB-6 — uninstall removes attribution hook, preserves a user value.
  @ab-6 @error @contract-shape:bounded-change
  Scenario: Uninstall removes the attribution hook and preserves a user credit
    Given a active repo
    And a user-modified legacy attribution credit in the Claude settings
    And the attribution commit hook is registered
    When the operator uninstalls nWave
    Then the attribution commit hook is not registered
    And the user-authored attribution credit is preserved unchanged
