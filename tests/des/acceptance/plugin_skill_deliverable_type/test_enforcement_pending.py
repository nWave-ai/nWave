"""Enforcement-gate binding -- plugin-skill-deliverable-type (step 01-02).

Binds the plugin/skill type-carried exemption scenarios from
``deliverable-type-enforcement.feature`` -- both `@driving_port`, focused
scenarios that drive the REAL ``PreToolUseService.validate`` gate (wired by
``service_factory.create_pre_tool_use_service(deliverable_type=...)``) and assert
the dispatch is waved through by deliverable TYPE, with no per-dispatch exemption
marker in play.

These were DISTILL RED scaffolds (VERIFIED RED-for-the-right-reason: AssertionError
at the ``des_enforcement_policy.py`` exempt-set scaffold, MISSING_FUNCTIONALITY --
see ``distill/red-classification.md``), then module-skip-parked so the suite rested
GREEN. The whole-project exemption short-circuit was implemented at the policy
boundary in step 01-01's walking skeleton (``EXEMPT_DELIVERABLE_TYPES`` ->
``is_enforced=False`` for the FULL ``{plugin, skill}`` set); step 01-02 activates
these focused service-port scenarios that prove that same wiring from the driving
port for BOTH exempt types.

A project-local ``@skip`` Gherkin tag does NOT work here: this repo's
``pytest_bdd_apply_tag`` hook (tests/conftest.py) applies a tag as a mark ONLY if
it is a registered marker, and ``skip`` is not registered -- an unregistered tag
is consumed (scenario still RUNS). A module-level ``pytestmark = pytest.mark.skip``
was the mechanism that parked the scenarios (verified), identical to the matrix
specs ``test_deliverable_type_{enforcement,detection}.py``.
"""

from pytest_bdd import scenario

from tests.des.acceptance.plugin_skill_deliverable_type.steps.steps_plugin_skill import *  # noqa: F403


_FEATURE = "deliverable-type-enforcement.feature"


@scenario(
    _FEATURE, "A plugin project runs a planned step without being policed or stamped"
)
def test_plugin_runs_planned_step_unstamped() -> None:
    """@driving_port: plugin type-carried exemption at the service port (no marker)."""


@scenario(_FEATURE, "A skill project runs a planned step without being policed")
def test_skill_runs_planned_step() -> None:
    """Skill type-carried exemption: planned step proceeds without markers."""
