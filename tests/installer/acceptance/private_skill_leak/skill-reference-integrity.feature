# Concern 4 — Prevention (regression guard).
#
# Skill references live in two channels: an agent's declared skill list,
# and free-text mentions in agent/skill bodies. Ownership is derived from
# only the first channel, so a public artifact can name a skill that no
# agent declares — and the privacy strip then drops it as orphan work,
# shipping a public package with a dangling reference.
#
# This validator closes the loop: every skill named by a public artifact
# must survive the privacy strip. It FAILS against current master (the
# two load-bearing public skills are dropped) and PASSES once they are
# made visible to public artifacts.
#
# @contract-shape:pure-function — the validator reads the framework source
# and returns the set of dangling references; it changes nothing.

@feature-fix-installer-private-skill-leak @concern-4
Feature: Public work never depends on work the release would remove

  As the maintainer of the public nwave-ai package
  I want a guard that every public artifact's skill is kept by the release
  So that public installs never ship a reference to missing work

  Background:
    Given the nWave framework source with private agents and skills

  @slice-04 @driving_port @real-io @contract-shape:pure-function
  Scenario: Every skill a public artifact names survives the release strip
    When the skill-reference guard inspects the framework source
    Then the guard finds no public artifact depending on removable work

  @slice-04 @driving_port @real-io @contract-shape:pure-function
  Scenario: The guard flags a public artifact that depends on removable work
    Given a framework source where a public artifact names a skill the release strip removes
    When the skill-reference guard inspects that framework source
    Then the guard names that public artifact and the removable skill it depends on
