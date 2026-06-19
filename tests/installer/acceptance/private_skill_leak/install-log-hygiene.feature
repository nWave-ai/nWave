# Concern 3 — Install-log hygiene.
# A public install must never disclose private agent/skill names in its
# output. Dev installs keep the per-skill diagnostic.
#
# @contract-shape:bounded-change — the install log is a bounded artifact;
# the change is "private names removed from the public log, aggregate
# count added", with the dev log otherwise unchanged.

@feature-fix-installer-private-skill-leak @concern-3
Feature: The public installer keeps private names out of its output

  As a customer installing nwave-ai
  I want the installer to report skipped skills without naming private work
  So that installing the public package never discloses internal IP

  Background:
    Given the nWave framework source with private agents and skills

  @slice-03 @driving_port @real-io
  Scenario: A customer installs the public package and sees no private names
    When a customer runs a public install
    Then the install output names no private agent
    And the install output names no private skill
    And the install output reports an aggregate count of skipped skills

  @slice-03 @driving_port @real-io
  Scenario: A framework developer still sees the per-skill skip diagnostic
    When a framework developer runs a developer install
    Then the install output may name skipped skills for the author's benefit

  @slice-03 @driving_port @real-io @contract-shape:bounded-change
  Scenario: Switching from developer to public install changes only the log detail
    Given a developer install has recorded its output
    When the same source is installed in public mode
    Then the public output discloses no private name that the developer output revealed
