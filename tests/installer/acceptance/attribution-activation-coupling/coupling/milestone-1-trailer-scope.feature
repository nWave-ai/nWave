@attribution-activation-coupling @trailer-scope
Feature: The nWave commit credit appears only where nWave is active
  The activation-gated commit path is the sole mechanism. A commit gets the dual
  credit iff Claude commits via Bash AND nWave is active in the repo AND the
  attribution preference is on. Anywhere else, no credit and no write to that
  repo's Claude surface.

  # AB-1 — load-bearing scope-change assertion (active repo gets the credit).
  @ab-1 @driving_port @contract-shape:bounded-change
  Scenario: Active repo with attribution on gets the dual credit (-m)
    Given a active repo
    And attribution preference is on
    When Claude commits with -m
    Then the commit carries the dual nWave credit
    And the committed message has exactly two co-author lines

  @ab-1 @driving_port @contract-shape:bounded-change
  Scenario: Active repo with attribution on gets the dual credit (&& chain)
    Given a active repo
    And attribution preference is on
    When Claude commits in an && chain
    Then the commit carries the dual nWave credit
    And the committed message has exactly two co-author lines

  # AB-2 — sticky opt-out: no credit AND nothing written to that repo's surface.
  @ab-2 @driving_port @error @contract-shape:unbounded-preservation
  Scenario: Inactive repo with sticky opt-out gets no credit
    Given a inactive repo
    And attribution preference is on
    When Claude commits with -m
    Then the commit carries no nWave credit
    And nothing is written to the Claude settings for that repo

  # AB-3 — non-nWave repo under opt-in default: inactive, no credit.
  @ab-3 @driving_port @error @contract-shape:unbounded-preservation
  Scenario: Non-nWave repo gets no credit under opt-in default
    Given a non-nWave repo
    And attribution preference is on
    When Claude commits with -m
    Then the commit carries no nWave credit
    And nothing is written to the Claude settings for that repo
