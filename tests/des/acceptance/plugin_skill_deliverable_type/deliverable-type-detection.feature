@plugin_skill_deliverable_type @driving_port @detection @real-io
Feature: A silent project is classified only by markers sitting at its very root

  When a project declares nothing, nWave guesses its deliverable type from
  tell-tale files -- but only those sitting directly at the project's root. A
  plugin manifest at the root marks a plugin; a skills folder at the root marks a
  skill; anything else is application code. Crucially, a skills folder buried
  inside a sub-folder is NOT a signal: an application project that merely ships
  some skills under a nested folder must never be mistaken for a skill project and
  silently let off discipline.

  Detection is read through the real root-only detector
  (deliverable_type_detector.detect_deliverable_type) over a real project tree on
  disk. The full marker table is exercised exhaustively in the companion
  parametrized specification (test_deliverable_type_detection.py).

  @contract-shape:unbounded-preservation
  Scenario: A root plugin manifest marks the project a plugin
    Given the project has a "CLAUDE_PLUGIN_DIR" at its root
    When the deliverable type is detected from the project tree
    Then the detected deliverable type is "PLUGIN"

  @contract-shape:unbounded-preservation
  Scenario: A root skills folder marks the project a skill
    Given the project has a "ROOT_SKILLS_DIR" at its root
    When the deliverable type is detected from the project tree
    Then the detected deliverable type is "SKILL"

  @contract-shape:unbounded-preservation
  Scenario: A root commands folder marks the project a skill
    Given the project has a "ROOT_COMMANDS_DIR" at its root
    When the deliverable type is detected from the project tree
    Then the detected deliverable type is "SKILL"

  @contract-shape:unbounded-preservation
  Scenario: A root hooks folder marks the project a skill
    Given the project has a "ROOT_HOOKS_DIR" at its root
    When the deliverable type is detected from the project tree
    Then the detected deliverable type is "SKILL"

  @contract-shape:unbounded-preservation @error
  Scenario: A nested skills folder is not a signal and discipline is preserved
    Given the project has a "NESTED_NWAVE_SKILLS" at its root
    When the deliverable type is detected from the project tree
    Then the detected deliverable type is "APPLICATION"

  @contract-shape:unbounded-preservation @error
  Scenario: A project with no markers is application code
    Given the project has a "NONE" at its root
    When the deliverable type is detected from the project tree
    Then the detected deliverable type is "APPLICATION"
