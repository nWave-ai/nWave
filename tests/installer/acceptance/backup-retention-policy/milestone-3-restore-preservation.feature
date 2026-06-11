# Feature: Backup Retention Policy — Milestone 3 (Restore preservation)
# Covers REQUIRED scenario S5 from
#   docs/feature/backup-retention-policy/discuss/scope.md

Feature: Backup retention preserves the restore experience for Marco
  As Marco, a solo developer iterating on nWave from my laptop
  I want --restore to keep working exactly as before, against the surviving backups
  So that retention never costs me the ability to recover from a botched edit

  Background:
    Given Marco has a clean Claude config home at the test sandbox

  @real-io @S5
  Scenario: After 11 successful installs, restore picks the most recent surviving backup
    Given Marco has 11 successful prior installs spanning several days
    And the maximum backup count is the default of 10
    And the install has just applied retention, removing the oldest backup
    When Marco asks the installer to restore from the most recent backup
    Then the restore picks the most recent surviving backup
    And Marco's agents directory contains the contents of that backup
    And Marco's commands directory contains the contents of that backup
    And the restore reports success
