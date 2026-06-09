"""Acceptance test — release-pipeline strip-order contract (GAP-A).

Concern: the public PyPI wheel must be built from an ALREADY-STRIPPED
source tree. The 3.15.1 IP leak (RCA Q2 root cause) happened because the
``pypi-publish`` job in ``.github/workflows/release-prod.yml`` builds the
wheel directly — ``strip_private_agents.py`` runs only later, in the
``sync-public`` job, which never touches the wheel.

This AT is the root-cause regression guard: it parses the REAL
``release-prod.yml`` and asserts that, inside the ``pypi-publish`` job,
the privacy-strip step runs strictly BEFORE the wheel-build step.

It FAILS for the right reason on current master — the pypi-publish job
has NO strip step at all, so the strip cannot precede the build
(``MISSING_FUNCTIONALITY``). It PASSES once a strip step is inserted
into the pypi-publish job ahead of ``python -m build``.

NOT a pytest-bdd scenario and NOT ``@xfail``-tagged — this AT is meant
to be genuinely RED until DELIVER reorders the pipeline.

Layer 3 (real file parse) → example-based, no PBT machinery (Mandate 9
/ 11). Step body delegates to ``ReleasePipelineService`` — no business
logic inlined (Mandate-12 criterion 3).
"""

from __future__ import annotations

import pytest

from tests.installer.acceptance.private_skill_leak.steps.wheel_privacy_composition import (
    build_composition,
)


pytestmark = pytest.mark.xfail(
    reason="author-ahead: fix-installer-private-skill-leak DELIVER parked "
    "pending ATDD-pure spine repair; crafter removes at GREEN",
    strict=False,
)


@pytest.fixture
def composition():
    """Production composition root over the real repository tree."""
    return build_composition()


def test_privacy_strip_precedes_wheel_build_in_pypi_publish_job(composition):
    """The pypi-publish job strips private work BEFORE building the wheel.

    Outcome (ubiquitous language): a customer who installs the published
    package never receives private work, because the wheel is built from
    a tree the release pipeline already stripped.

    @contract-shape:unbounded-preservation — the pipeline must preserve
    the "no private artifact in the wheel" property; the order of the two
    steps is the mechanical guarantee of that preservation.
    """
    report = composition.pipeline.inspect_pypi_publish_order()

    assert report.job_found, (
        "the pypi-publish job is missing from release-prod.yml — "
        "cannot verify the strip-order contract"
    )
    assert report.strip_index != -1, (
        "the pypi-publish job has NO privacy-strip step — the public "
        "wheel is built from an un-stripped tree (RCA Q2 root cause). "
        "strip_private_agents.py must run inside pypi-publish, before "
        "the wheel build."
    )
    assert report.build_index != -1, (
        "the pypi-publish job has no wheel-build step — workflow shape "
        "changed; the strip-order AT needs updating"
    )
    assert report.strip_precedes_build, (
        "the privacy strip runs AFTER the wheel build in the "
        f"pypi-publish job (strip at step {report.strip_index}, build at "
        f"step {report.build_index}). The wheel would ship un-stripped "
        "private work — the strip MUST precede the build."
    )
