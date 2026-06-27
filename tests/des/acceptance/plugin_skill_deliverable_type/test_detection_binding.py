"""Root-only detection binding -- plugin-skill-deliverable-type (DISTILL scaffold).

Binds ``deliverable-type-detection.feature`` to the shared step vocabulary.
A silent project is classified only by markers at its very root; a nested
``nWave/skills/`` is never a signal (the collision guard).

ALL scenarios here are not-yet-implemented (RED against the
``deliverable_type_detector`` ``__SCAFFOLD__``), so the whole module is parked
under a module-level skip -- the committable resting state (ADR-025 One-at-a-Time).
They were VERIFIED RED-for-the-right-reason (AssertionError at
``deliverable_type_detector.py:40`` -- MISSING_FUNCTIONALITY, see
``distill/red-classification.md``) before being parked. DELIVER removes this
``pytestmark`` and greens root-only detection.

A project-local ``@skip`` Gherkin tag does NOT work here: this repo's
``pytest_bdd_apply_tag`` hook applies a tag as a mark ONLY if it is a registered
marker, and ``skip`` is not registered -- so a ``@skip`` tag would be consumed and
the scenarios would still RUN. The module-level ``pytestmark`` is the verified
mechanism (identical to the matrix specs).
"""

from pytest_bdd import scenarios

from tests.des.acceptance.plugin_skill_deliverable_type.steps.steps_plugin_skill import *  # noqa: F403


scenarios("deliverable-type-detection.feature")
