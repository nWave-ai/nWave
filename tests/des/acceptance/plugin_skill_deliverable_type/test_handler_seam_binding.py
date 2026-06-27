"""Handler-seam binding (PENDING RED, the walking skeleton) -- plugin-skill-deliverable-type.

Binds ``deliverable-type-handler-seam.feature`` -- the `@driving_adapter`
`@walking_skeleton` scenario that drives the REAL Claude Code hook entry point
(`pre_tool_use_handler.handle_pre_tool_use`) end-to-end for a plugin-declared
project. This is the ONE layer the lower scaffolds do not cover: HIGH-1 from the
DESIGN review -- without it, DELIVER could green every lower scaffold and the
feature stays silently inert (the handler keeps passing ``None`` -> enforcement
always ON).

Module-level skip is the committable resting state (ADR-025 One-at-a-Time). The
scenario was VERIFIED RED-for-the-right-reason: a plugin project's planned-step
dispatch through the real handler is currently BLOCKED (exit 2) because the
handler's ``_resolve_deliverable_type`` returns ``None`` (the seam is a no-behavior
``__SCAFFOLD__`` that keeps all 180 existing handler tests green). DELIVER wires
``_resolve_deliverable_type`` to read ``DESConfig(cwd).deliverable_type`` and the
dispatch is allowed (exit 0) -- it cannot green this scenario without wiring the
handler. RED comes from the SCENARIO, never from a raising read on the hot path.

This is the feature's true walking skeleton (the user's actual invocation path,
RCA fix P1); the service-level plugin scenario is now a focused `@driving_port`
scenario, not the WS.
"""

from pytest_bdd import scenario

from tests.des.acceptance.plugin_skill_deliverable_type.steps.steps_plugin_skill import *  # noqa: F403


_FEATURE = "deliverable-type-handler-seam.feature"


@scenario(_FEATURE, "The hook lets a plugin project's planned step proceed")
def test_hook_allows_plugin_planned_step() -> None:
    """@walking_skeleton @driving_adapter: the issue headline at the real hook seam."""
