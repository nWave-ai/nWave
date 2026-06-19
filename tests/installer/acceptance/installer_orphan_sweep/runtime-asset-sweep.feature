# Feature: installer-orphan-sweep — slice-02 (runtime-asset families)
# Spec SSOT: docs/feature/installer-orphan-sweep/feature-delta.md (slice-02)
# Evidence:  docs/analysis/installer-upgrade-orphan-analysis-2026-06-11.md
#            (incl. the 2026-06-11 correction note on utilities_plugin.py)
# Driving port: PluginRegistry.install_all(InstallContext) — the production
# plugin pipeline for the families sharing ~/.claude target directories
# (templates, utilities, des in dependency order), real filesystem in tmp_path.

Feature: Installed runtime assets match the shipped version exactly
  As a user upgrading nWave
  I want exactly the runtime assets the new version ships, for every asset family
  So that retired assets cannot linger and act stale, while everything I created myself stays untouched

  @slice-02 @acceptance @driving_port @real-io @contract-shape:bounded-change
  Scenario: Upgrade removes a runtime asset folder the new version no longer ships
    Given a previous nWave version installed its runtime assets with a manifest
    And the previous version had installed the runtime asset folder "legacy-flavors" which the new version no longer ships
    When the user upgrades nWave
    Then the runtime asset folder "legacy-flavors" is no longer installed
    And the runtime assets of the current version are installed
    And every asset family's manifest lists exactly what this version ships

  @slice-02 @acceptance @driving_port @real-io @contract-shape:bounded-change
  Scenario: A template the user created survives an upgrade untouched
    Given a previous nWave version installed its runtime assets with a manifest
    And the user keeps a personal template "my-team-conventions.md" alongside the installed runtime assets
    When the user upgrades nWave
    Then "my-team-conventions.md" is still present with its original content
    And every asset family's manifest lists exactly what this version ships

  @slice-02 @acceptance @driving_port @real-io @contract-shape:bounded-change
  Scenario: No part of an upgrade touches the user's personal script
    Given a previous nWave version installed its DES scripts with a manifest
    And the user keeps a personal script "my_backup_tool.py" alongside the installed scripts
    When the user upgrades nWave
    Then "my_backup_tool.py" is still present with its original content
    And the user is warned that unrecorded scripts were preserved
    And every asset family's manifest lists exactly what this version ships
