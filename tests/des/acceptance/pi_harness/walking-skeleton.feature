@walking_skeleton @driving_port
Feature: nWave DES enforcement loads into the pi coding agent
  As a developer using pi (a minimal, subagent-less harness)
  I want the nWave DES extension to load when I start pi in an nWave project
  So that the path pi -> extension -> Python DES engine is wired end to end

  Scenario: Starting pi in an activated project confirms DES enforcement is live
    Given an nWave-activated project
    And the nWave pi DES extension rendered for that project
    When I start pi with the extension loaded
    Then pi reports that DES enforcement is active for pi
