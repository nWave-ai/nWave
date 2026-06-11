# Feature: installer-orphan-sweep — slice-01 (DES scripts manifest)
# Spec SSOT: docs/feature/installer-orphan-sweep/feature-delta.md (slice-01)
# Evidence:  docs/analysis/installer-upgrade-orphan-analysis-2026-06-11.md
# Driving port: DESPlugin.install(InstallContext) — the public install path
# for the DES scripts family, real filesystem in tmp_path.

Feature: Installed DES scripts match the shipped version exactly
  As a user upgrading nWave
  I want exactly the DES scripts the new version ships
  So that scripts retired from the product cannot linger on my machine and act stale

  @slice-01 @acceptance @driving_port @real-io @contract-shape:bounded-change
  Scenario: Fresh install records every DES script it installs
    Given a machine where nWave has never been installed
    When the user installs nWave
    Then the DES scripts of the current version are installed
    And the installation manifest lists exactly the installed DES scripts

  @slice-01 @walking_skeleton @acceptance @driving_port @real-io @contract-shape:bounded-change
  Scenario: Upgrade removes a DES script the new version no longer ships
    Given a previous nWave version installed its DES scripts with a manifest
    And the previous version had installed "retired_helper.py" which the new version no longer ships
    When the user upgrades nWave
    Then "retired_helper.py" is no longer among the installed DES scripts
    And the DES scripts of the current version are installed
    And the installation manifest lists exactly the installed DES scripts

  @slice-01 @acceptance @driving_port @real-io @contract-shape:bounded-change
  Scenario: Upgrading a manifest-less installation preserves unknown scripts and warns
    Given a nWave installation from a version that kept no manifest
    And the user keeps a personal script "my_backup_tool.py" alongside the installed scripts
    When the user upgrades nWave
    Then "my_backup_tool.py" is still present with its original content
    And the user is warned that unrecorded scripts were preserved
    And the installation manifest lists exactly the installed DES scripts
