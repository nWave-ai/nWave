"""Walking-skeleton e2e: the public wheel carries no `public: false` artifact.

Feature: fix-installer-private-skill-leak, slice-01 (`@walking_skeleton`).

This is the GENUINE end-to-end test required by G-WIRING-1 (friction log
``docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md``, "Hard gates
to add"): the slice-01 walking-skeleton ATs in
``tests/installer/acceptance/private_skill_leak/`` run the privacy strip
*in-process* against a copied tree — they verify the strip FUNCTION, not the
release PIPELINE. They never inspect a real ``.whl``.

This test closes two gaps:

  * GAP-D — the existing slice-01 ATs inspect a tree the test itself strips;
    they never build the artifact a customer actually receives.
  * the e2e-layer gap — ``tests/e2e/test_wheel_privacy_contract.py`` asserts
    PATH-CLASSES (no ``docs/analysis/``, no ``src/des/`` ...) but never asserts
    that no ``public: false`` AGENT or privately-owned SKILL ships.

Mechanism — subprocess-real, no Fixture Theater:

  * The ``pypi_shape_wheel`` session fixture (``tests/e2e/conftest.py``)
    builds a real PyPI-shape ``.whl`` by running the EXACT release pipeline
    as subprocesses: ``build_dist.py`` → ``patch_pyproject.py`` →
    ``python -m build --wheel``. No live PyPI, no in-process strip.
  * This test then unzips that real ``.whl`` and inspects the shipped
    ``nWave/agents/`` and ``nWave/skills/`` against the catalog allow-list.

Contract asserted (slice-01 core, both halves — they are inseparable):

  1. PRIVACY — zero agent flagged ``public: false`` in
     ``framework-catalog.yaml`` survives into the wheel; zero privately-owned
     skill directory survives.
  2. SURVIVAL — every load-bearing public skill in
     ``scripts.shared.agent_catalog.PUBLIC_SHARED_SKILLS`` (the 11 skills with
     no owning public agent that public installs still depend on) survives.

Expected result on the current tree: see the module docstring's "Pipeline
gap" note below — if the release pipeline does not strip before
``python -m build``, this test is RED, and that RED is the finding, not a
test bug. Slice-01's in-process ATs cannot see this because they strip the
tree themselves before inspecting it.

Tagged ``@slice-01 @walking_skeleton @wiring_e2e`` — this IS the slice-01
walking skeleton for fix-installer-private-skill-leak. It is the genuine
end-to-end test: real composition root, real release pipeline run as
subprocesses, real ``.whl`` unzipped and inspected. It supersedes the
fixture-folded in-process ``@walking_skeleton`` scenario that previously
lived in ``wheel-privacy.feature`` (that scenario stripped a tree the test
itself copied and never built an artifact a customer receives — false
GREEN by construction).

Mutation-flippability is the litmus: deleting the privacy-strip call in
``scripts/release/patch_pyproject.py`` (or its force-include) must flip
this test RED. Verified 2026-05-20.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.shared.agent_catalog import (
    PUBLIC_SHARED_SKILLS,
    build_ownership_map,
    detect_command_skills,
    is_public_skill,
    load_private_agents,
    load_public_agents,
)


pytestmark = [
    pytest.mark.wiring_e2e,
    pytest.mark.e2e,
    pytest.mark.walking_skeleton,
    pytest.mark.slice_01,
]

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_NWAVE_DIR = _REPO_ROOT / "nWave"


def _wheel_agent_files(wheel: Path) -> set[str]:
    """Bare agent filenames (``nw-*.md``) shipped under ``nWave/agents/``."""
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    return {
        Path(n).name
        for n in names
        if n.startswith("nWave/agents/nw-") and n.endswith(".md")
    }


def _wheel_skill_dirs(wheel: Path) -> set[str]:
    """Skill directory names (``nw-*``) shipped under ``nWave/skills/``."""
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    dirs: set[str] = set()
    for n in names:
        if not n.startswith("nWave/skills/nw-"):
            continue
        # nWave/skills/<skill-dir>/...  -> take the third path segment
        parts = n.split("/")
        if len(parts) >= 3 and parts[2].startswith("nw-"):
            dirs.add(parts[2])
    return dirs


@pytest.mark.e2e
class TestSlice01WheelPrivateArtifactContract:
    """slice-01 walking-skeleton: real wheel excludes private work, keeps public.

    Class name carries ``Slice01`` so ``pytest -k slice-01`` (and
    ``-k slice01``) collects this walking skeleton alongside the Gherkin
    slice-01 scenarios.
    """

    def test_wheel_ships_no_private_agent(self, pypi_shape_wheel: Path) -> None:
        """No agent flagged ``public: false`` in the catalog survives the build.

        Builds the real ``.whl`` via the release pipeline (the
        ``pypi_shape_wheel`` fixture) and unzips it. Each leaked private
        agent is a v3.15.1-class IP disclosure.
        """
        private_agents = load_private_agents(_NWAVE_DIR)
        assert private_agents, (
            "catalog reports zero private agents — fixture-of-record broken"
        )

        shipped = _wheel_agent_files(pypi_shape_wheel)
        # An agent file is named nw-<name>.md; the catalog keys are bare names.
        shipped_bare = {n.removeprefix("nw-").removesuffix(".md") for n in shipped}
        leaked = sorted(private_agents & shipped_bare)

        assert leaked == [], (
            f"public wheel leaked {len(leaked)} private agent(s): {leaked}\n"
            f"wheel: {pypi_shape_wheel}\n"
            "These are flagged `public: false` in nWave/framework-catalog.yaml "
            "and must never reach the public PyPI package (v3.15.1 RCA class)."
        )

    def test_wheel_ships_no_private_skill(self, pypi_shape_wheel: Path) -> None:
        """No privately-owned skill directory survives into the wheel.

        A skill is private when none of its owning agents is public AND it
        is not a command-skill nor a load-bearing public-shared skill. The
        ownership map is derived from agent frontmatter — the same SSOT the
        production strip uses.
        """
        public_agents = load_public_agents(_NWAVE_DIR, strict=True)
        ownership_map = build_ownership_map(_NWAVE_DIR / "agents")
        command_skills = detect_command_skills(_NWAVE_DIR / "skills")

        shipped = _wheel_skill_dirs(pypi_shape_wheel)
        leaked = sorted(
            s
            for s in shipped
            if not is_public_skill(
                s,
                public_agents,
                ownership_map=ownership_map,
                command_skills=command_skills,
            )
        )

        assert leaked == [], (
            f"public wheel leaked {len(leaked)} private skill(s): {leaked}\n"
            f"wheel: {pypi_shape_wheel}\n"
            "No public agent owns these skills and they are not command-skills "
            "— they are private work and must not ship."
        )

    def test_wheel_keeps_every_load_bearing_public_skill(
        self, pypi_shape_wheel: Path
    ) -> None:
        """Every PUBLIC_SHARED_SKILLS entry survives the build (no dangling refs).

        The privacy strip removes private work; it must NOT drop the 11
        load-bearing public skills that have no owning public agent but that
        public installs depend on. Dropping them ships a public package with
        a dangling skill reference (RCA Q4). Privacy and survival are the two
        inseparable halves of slice-01.
        """
        shipped = _wheel_skill_dirs(pypi_shape_wheel)
        missing = sorted(s for s in PUBLIC_SHARED_SKILLS if s not in shipped)

        assert missing == [], (
            f"public wheel dropped {len(missing)} load-bearing public "
            f"skill(s): {missing}\n"
            f"wheel: {pypi_shape_wheel}\n"
            "These are public methodology skills with no owning public agent; "
            "public installs depend on them. The strip must preserve them."
        )
