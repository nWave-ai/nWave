@attribution-activation-coupling
Feature: Attribution credit follows per-repo nWave activation
  As a developer using nWave across many repositories
  I want the nWave commit credit to appear only where nWave is active
  So that my commits in unrelated repos are never silently branded

  # Walking skeleton — the one demo-able end-to-end journey that proves the
  # feature's core value (Pillar 2 chained narrative): an operator installs
  # nWave, and a commit in an ACTIVE repo carries the dual credit. This drives
  # the real install plugin + the real activation gate + the real commit
  # rewriter end-to-end. A non-technical stakeholder confirms: "yes — after
  # installing, my nWave commits are credited." The per-repo SCOPE (no credit in
  # an inactive repo) is the milestone-1 sibling that completes the story.

  @walking_skeleton @driving_adapter @real-io @contract-shape:bounded-change
  Scenario: After installing, a commit in an active repo carries the dual credit
    Given a active repo
    And attribution preference is on
    When the operator installs nWave
    And Claude commits with -m
    Then the commit carries the dual nWave credit
    And the committed message has exactly two co-author lines
