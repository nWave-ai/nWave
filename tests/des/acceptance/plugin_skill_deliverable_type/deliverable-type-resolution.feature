@plugin_skill_deliverable_type @driving_port @resolution
Feature: A project's deliverable type is resolved from what it declares first

  A project states its deliverable type in its own settings; a machine-wide
  default can stand in when the project says nothing; and only when nothing is
  stated does nWave fall back to inspecting the project for tell-tale markers. A
  mis-spelled declaration is never honoured silently -- it is set aside with a
  warning and resolution carries on as if nothing was declared. When nothing at
  all resolves, the answer is an explicit "no opinion", which is kept distinct
  from a project that positively declares itself application code.

  Resolution is read through the real settings reader (DESConfig.deliverable_type,
  the driving port).

  @contract-shape:pure-function
  Scenario: A project's own declaration is honoured
    Given the project declares its deliverable type as "PROJECT_PLUGIN"
    When the deliverable type is resolved for this project
    Then the resolved deliverable type is "PLUGIN"

  @contract-shape:pure-function
  Scenario: A skill declaration is honoured
    Given the project declares its deliverable type as "PROJECT_SKILL"
    When the deliverable type is resolved for this project
    Then the resolved deliverable type is "SKILL"

  @contract-shape:pure-function
  Scenario: A machine-wide default stands in when the project is silent
    Given the project declares its deliverable type as "GLOBAL_PLUGIN"
    When the deliverable type is resolved for this project
    Then the resolved deliverable type is "PLUGIN"

  @contract-shape:pure-function @error
  Scenario: A mis-spelled declaration is set aside to the safe default
    Given the project declares its deliverable type as "PROJECT_TYPO"
    When the deliverable type is resolved for this project
    Then the resolved deliverable type is "NONE"

  @contract-shape:unbounded-preservation @error
  Scenario: A mis-spelled declaration is not rescued by a root skills folder
    Given the project declares its deliverable type as "PROJECT_TYPO_WITH_ROOT_SKILLS"
    When the deliverable type is resolved for this project
    Then the resolved deliverable type is "NONE"

  @contract-shape:pure-function @error
  Scenario: A silent project with no markers resolves to no opinion
    Given the project declares its deliverable type as "ABSENT"
    When the deliverable type is resolved for this project
    Then the resolved deliverable type is "NONE"
