@plugin_skill_deliverable_type @driving_adapter @enforcement
Feature: The real hook entry point honours a plugin project's deliverable type

  The enforcement decision must reach the practitioner through the REAL hook the
  editor fires -- not only through the inner service. When the editor fires its
  pre-dispatch hook for a project that declares on disk that it builds a plugin,
  and the dispatch runs a planned step with no markers, the hook must let it
  proceed. If only the inner service knew about deliverable types but the hook
  kept policing every dispatch, the whole feature would be silently inert.

  This scenario drives the real hook entry point end-to-end (a hook payload ->
  `handle_pre_tool_use` -> the production service factory), with the plugin
  declaration sitting on disk under the dispatch's working directory, so the hook
  must read it for the exemption to take effect. The observable is the hook's
  process exit (allowed vs blocked).

  @contract-shape:pure-function @walking_skeleton
  Scenario: The hook lets a plugin project's planned step proceed
    Given a project on disk that declares it builds a plugin
    When the hook fires for a planned step with no markers
    Then the dispatch is allowed to proceed
