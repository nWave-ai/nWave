# Feature: Backup Retention Policy — Milestone 1 (Core retention behavior)
# Covers REQUIRED scenarios S1, S2, S3, S6 from
#   docs/feature/backup-retention-policy/discuss/scope.md

Feature: Backup retention enforces a sane cap on accumulated backups
  As Marco, a solo developer iterating on nWave from my laptop
  I want a clear, predictable rule for how many backups stay on disk
  So that I never have to manually clean up backups to reclaim space

  Background:
    Given Marco has a clean Claude config home at the test sandbox

  @real-io @S1
  Scenario: Fresh install on a bare system creates no backup at all
    Given Marco has no prior nWave install in his Claude config home
    When Marco runs the install backup phase
    Then no backup directory matching "nwave-*" exists in his backups area
    And the install backup phase reports nothing was backed up

  @real-io @S2
  Scenario: Second install creates a second backup without pruning
    Given Marco has exactly 1 prior backup named "nwave-install-20260101-100000"
    And no override exists for the maximum backup count
    And a new backup directory "nwave-install-20260102-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then no backup directory was removed
    And exactly 2 backup directories remain on disk
    And both prior and new backups are still present

  @real-io @S3
  Scenario: Eleventh install with default cap=10 prunes the oldest, foreign dirs untouched
    Given Marco has 10 backup directories from prior installs:
      | nwave-install-20260101-100000 |
      | nwave-install-20260102-100000 |
      | nwave-install-20260103-100000 |
      | nwave-install-20260104-100000 |
      | nwave-install-20260105-100000 |
      | nwave-install-20260106-100000 |
      | nwave-install-20260107-100000 |
      | nwave-install-20260108-100000 |
      | nwave-install-20260109-100000 |
      | nwave-install-20260110-100000 |
    And Marco has a personal directory "manual-pre-experiment" alongside his backups
    And no override exists for the maximum backup count
    And a new backup directory "nwave-install-20260111-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then the oldest backup "nwave-install-20260101-100000" is removed from disk
    And exactly 10 backup directories remain on disk
    And the surviving backups are "nwave-install-20260102-100000" through "nwave-install-20260111-100000"
    And Marco's "manual-pre-experiment" directory is still present and untouched

  @real-io @S6
  Scenario: Pool sums across install, uninstall, and update backup types
    Given Marco has 8 backup directories named "nwave-install-20260101-100000" through "nwave-install-20260108-100000"
    And Marco has 2 backup directories named "nwave-uninstall-20260109-100000" and "nwave-uninstall-20260110-100000"
    And no override exists for the maximum backup count
    And a new backup directory "nwave-install-20260111-100000" has just been created by the install
    When Marco lets the install apply its retention policy
    Then the lex-smallest of the 10 prior "nwave-*" directories is removed
    And exactly 10 backup directories matching "nwave-*" remain on disk
    And the pruned directory is "nwave-install-20260101-100000"
