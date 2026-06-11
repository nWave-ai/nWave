# Feature: Backup Retention Policy — Milestone 2 (Config overrides + validation)
# Covers REQUIRED scenarios S4 and S9 from
#   docs/feature/backup-retention-policy/discuss/scope.md

Feature: Marco can override the backup cap in his global nWave config
  As Marco, a solo developer iterating on nWave from my laptop
  I want to tune the backup cap to match my disk budget
  So that I can keep more or fewer backups according to my own constraints

  Background:
    Given Marco has a clean Claude config home at the test sandbox

  @real-io @S4
  Scenario: Marco sets the cap to 5 and the install enforces it
    Given Marco has set the maximum backup count to 5 in his nWave global config
    And Marco has 5 backup directories from prior installs:
      | nwave-install-20260101-100000 |
      | nwave-install-20260102-100000 |
      | nwave-install-20260103-100000 |
      | nwave-install-20260104-100000 |
      | nwave-install-20260105-100000 |
    And a new backup directory "nwave-install-20260106-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then exactly 5 backup directories remain on disk
    And the oldest backup "nwave-install-20260101-100000" is removed from disk

  @real-io @S4
  Scenario: Marco sets the cap to 1 and only the newest backup survives
    Given Marco has set the maximum backup count to 1 in his nWave global config
    And Marco has 3 backup directories from prior installs:
      | nwave-install-20260101-100000 |
      | nwave-install-20260102-100000 |
      | nwave-install-20260103-100000 |
    And a new backup directory "nwave-install-20260104-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then exactly 1 backup directory remains on disk
    And the surviving backup is "nwave-install-20260104-100000"

  @real-io @S4
  Scenario: Marco sets the cap to 0 and every backup is removed after this install
    Given Marco has set the maximum backup count to 0 in his nWave global config
    And a new backup directory "nwave-install-20260104-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then no backup directory matching "nwave-*" remains on disk

  @real-io @S9
  Scenario: Negative cap value is rejected with a clear error before any backup is touched
    Given Marco has set the maximum backup count to -3 in his nWave global config
    And a new backup directory "nwave-install-20260104-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then the install reports a clear error mentioning "max_count" and the value "-3"
    And the new backup directory is still present on disk
    And no prior backup directory was removed

  @real-io @S9
  Scenario: Non-integer cap value is rejected with a clear error
    Given Marco has set the maximum backup count to "ten" in his nWave global config
    And a new backup directory "nwave-install-20260104-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then the install reports a clear error mentioning "max_count" and the value "ten"
    And the new backup directory is still present on disk

  @real-io @S9
  Scenario: Missing cap key falls back to the default of 10 silently
    Given Marco has a nWave global config with no maximum backup count set
    And Marco has 11 backup directories from prior installs spanning several days
    When Marco lets the install apply its retention policy
    Then exactly 10 backup directories remain on disk
    And no error or warning about the maximum backup count is reported
