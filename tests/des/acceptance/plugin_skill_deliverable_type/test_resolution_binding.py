"""Config-resolution binding -- plugin-skill-deliverable-type (DISTILL scaffold).

Binds the POSITIVE-resolution scenarios of ``deliverable-type-resolution.feature``
to the shared step vocabulary. Resolution precedence: project declaration ->
global default -> detection (ADR-PST-002).

``scenario()`` (singular) binds each positive scenario by exact title -- a
per-scenario binding (mirroring ``test_enforcement_binding.py``) that lets the
RED siblings be parked separately. Steps 01-01 + 01-03 green the positive
resolution path:
  1. a project's own declaration is honoured (project-plugin / project-skill);
  2. a machine-wide default stands in when the project is silent (global-plugin).

The not-yet-built scenarios are parked OUT of this module (not bound, not
skipped):
  - the mis-spelled / fail-safe scenarios (PROJECT_TYPO, PROJECT_TYPO_WITH_ROOT_
    SKILLS, ABSENT) -> step 03-02;
  - detection-fallback -> phase 02.
DELIVER binds those as their steps land.

CONTRACT_SHAPE_NOTE (phase-01 review D1): the deferred
"A mis-spelled declaration is not rescued by a root skills folder" scenario is
tagged @contract-shape:unbounded-preservation. When step 03-02 binds it, its
Then step MUST assert via assert_state_delta over the full universe
(project_config.text, global_config.text, resolved_type, gate.outcome, and a
root FS-tree-hash proving no mutation) -- a single resolved_type slot assertion
would be a Contract Shape compliance failure at activation.
"""

from pytest_bdd import scenario

from tests.des.acceptance.plugin_skill_deliverable_type.steps.steps_plugin_skill import *  # noqa: F403


_FEATURE = "deliverable-type-resolution.feature"


@scenario(_FEATURE, "A project's own declaration is honoured")
def test_project_declaration_is_honoured() -> None:
    """A project-local ``deliverable_type: plugin`` resolves to PLUGIN."""


@scenario(_FEATURE, "A skill declaration is honoured")
def test_skill_declaration_is_honoured() -> None:
    """A project-local ``deliverable_type: skill`` resolves to SKILL."""


@scenario(_FEATURE, "A machine-wide default stands in when the project is silent")
def test_global_default_stands_in() -> None:
    """A silent project falls back to the global ``defaults.deliverable_type``."""


# ---------------------------------------------------------------------------
# Fail-safe (@error) resolution scenarios -- step 03-02. A present-but-bad
# declaration is set aside to the SAFE DEFAULT (None, enforcement ON) WITHOUT
# falling through to detection (ADR-PST-002 step 4 / NB-2); a fully-absent
# declaration with no markers resolves to the explicit "no opinion" None. The
# shared ``Then`` asserts via full-universe ``assert_state_delta`` (Mandate 8),
# which also discharges the @contract-shape:unbounded-preservation obligation
# (D1): the typo+root-``skills/`` resolution must mutate nothing on disk.
# ---------------------------------------------------------------------------


@scenario(_FEATURE, "A mis-spelled declaration is set aside to the safe default")
def test_typo_resolves_to_safe_default() -> None:
    """A typo'd ``deliverable_type`` ('plugn') resolves to the safe default None.

    CONTRACT_SHAPE: unbounded-preservation
    """


@scenario(_FEATURE, "A mis-spelled declaration is not rescued by a root skills folder")
def test_typo_not_rescued_by_root_skills() -> None:
    """A typo'd declaration short-circuits to None BEFORE detection is consulted.

    CONTRACT_SHAPE: unbounded-preservation
    """


@scenario(_FEATURE, "A silent project with no markers resolves to no opinion")
def test_silent_project_resolves_to_none() -> None:
    """A fully-absent declaration with no markers resolves to the None sentinel.

    CONTRACT_SHAPE: unbounded-preservation
    """
