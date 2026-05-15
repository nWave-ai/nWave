# Regression — P0: installer reports green while disk state diverges from source.
# RCA: docs/feature/fix-installer-silent-template-skip/discuss/wave-decisions.md
#   Root Cause A — verifier uses existence-check, never content-check (install_nwave.py:608)
#   Root Cause B — filter_public_skills drops orphan/private skills with zero diagnostic
#                  (scripts/shared/skill_distribution.py:100, skills_plugin.py:217)
#
# Pre-fix: both scenarios PASS the installer ("verified", returncode 0) — bug.
# Post-fix (M1 + M2): both scenarios fail loud with file path / skipped name + reason.
#
# Driving ports:
#   Scenario A — NWaveInstaller.validate_installation()        (verifier loop)
#   Scenario B — SkillsPlugin.install(InstallContext)          (filter diagnostic)
#
# State-delta universe per Mandate Paradigm 2026-05-05:
#   A: {verifier_returned_ok, log_contains_drift_marker, log_names_drifted_file}
#   B: {log_contains_skipped_marker, log_names_filtered_skill, log_states_reason}

Feature: Installer verifier must detect content drift and report filtered skills

  As a framework maintainer
  I need the installer to fail loud when target content diverges from source
  And to log every skill filtered out by the public-agent policy
  So that "✅ Templates verified" cannot certify a target that is actually stale
  And authors of new skills see why their skill never reached ~/.claude/

  @bug-installer-silent-verifier @driving_port @rca-root-cause-A
  Scenario: Verifier detects content drift on a target template and fails with file name
    Given the installer source tree has a template "deliver-outside-in-tdd.yaml" with known content
    And the target tree has the same-named template but with one byte mutated
    And every other verifier check is configured to pass
    When the installer's validate_installation driving port is invoked
    Then the verifier reports installation as NOT verified
    And the verifier log contains a content drift marker
    And the verifier log names the drifted template file

  @bug-installer-silent-verifier @driving_port @rca-root-cause-B
  Scenario: Skills plugin logs every skill dropped by the public-agent filter
    Given the source tree has a public-owned skill "nw-keep-me" and an orphan skill "nw-drop-me"
    And the public-agent catalog excludes "nw-drop-me" from distribution
    When the skills plugin's install driving port is invoked with the filter active
    Then the install log contains a "Skipped" diagnostic for "nw-drop-me"
    And the install log states the filter as the reason
    And "nw-drop-me" is absent from the installation target
