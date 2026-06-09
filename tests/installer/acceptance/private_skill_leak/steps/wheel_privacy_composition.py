"""Composition root + services for the private-skill-leak acceptance suite.

Mandate-12: business logic lives here as the single source of truth.
Step methods (Tier A Gherkin steps + the release ATs) delegate to these
services and never inline logic.

Three production driving ports are exercised:

  1. ``scripts.release.strip_private_agents.strip`` — EXISTS today. The
     privacy strip. Concern 1 + 2.
  2. ``scripts.release.verify_wheel_privacy.verify`` — DOES NOT EXIST yet.
     RED scaffold created by DISTILL. The wheel-privacy gate (RCA Fix 1
     hardening). Concern 1.
  3. ``scripts.validation.validate_skill_references.check_references`` —
     DOES NOT EXIST yet. RED scaffold created by DISTILL. The dangling-ref
     prevention validator (RCA Fix 3 structural prevention). Concern 4.

The install-log hygiene concern (3) is exercised through the real
installer ``SkillsPlugin`` composition (production DI), see
``InstallLogService`` below.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from tests.installer.acceptance.private_skill_leak.steps.domain_types import (
    PRIVATE_AGENT_FILES,
    PRIVATE_SKILL_DIRS,
    InstallMode,
    SkillName,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Observable result types (port-exposed — these ARE the universe)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WheelContents:
    """The artifact set present inside a (simulated) public wheel tree.

    Observable, port-exposed names. The ATs assert against these fields
    only — never against private module internals.
    """

    agent_files: frozenset[str]
    skill_dirs: frozenset[str]

    def contains_agent(self, name: str) -> bool:
        return name in self.agent_files

    def contains_skill(self, name: str) -> bool:
        return name in self.skill_dirs


@dataclass(frozen=True)
class InstallLog:
    """The observable stdout of an installer run.

    ``lines`` is the captured log; ``skipped_count`` is the aggregate
    count the public installer is allowed to report.
    """

    lines: tuple[str, ...]
    skipped_count: int

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


# ---------------------------------------------------------------------------
# Service 1 — wheel build simulation + privacy strip (concerns 1 + 2)
# ---------------------------------------------------------------------------


class WheelBuildService:
    """Builds a public-wheel tree by applying the privacy strip.

    SSOT for "what ends up in the wheel". Mirrors the release pipeline:
    a source tree is copied, the strip is applied, and the surviving
    ``nWave/agents`` + ``nWave/skills`` are the wheel contents.
    """

    def __init__(self, source_repo_root: Path) -> None:
        self._source = source_repo_root

    def build_stripped_wheel_tree(self, dest: Path) -> Path:
        """Copy nWave/ into *dest* and apply the privacy strip.

        Returns the target dir (root containing ``nWave/``). This is the
        RCA Fix 1 contract: the wheel is built from a STRIPPED tree.
        """
        from scripts.release.strip_private_agents import strip

        target = dest / "wheel-tree"
        shutil.copytree(
            self._source / "nWave",
            target / "nWave",
            dirs_exist_ok=True,
        )
        strip(target)
        return target

    def build_unstripped_wheel_tree(self, dest: Path) -> Path:
        """Copy nWave/ into *dest* WITHOUT applying the privacy strip.

        Models the master-branch release path (RCA Q2 root cause): the
        ``pypi-publish`` job builds the wheel from an un-stripped tree.
        Used to exercise the privacy gate against a leaking package.
        """
        target = dest / "unstripped-wheel-tree"
        shutil.copytree(
            self._source / "nWave",
            target / "nWave",
            dirs_exist_ok=True,
        )
        return target

    def reprepare_wheel_tree(self, wheel_tree: Path) -> Path:
        """Apply the privacy strip again to an already-prepared tree.

        Idempotency contract (AT-completeness C4a): preparing the public
        package a second time must be a no-op — same surviving artifacts.
        """
        from scripts.release.strip_private_agents import strip

        strip(wheel_tree)
        return wheel_tree

    def read_wheel_contents(self, wheel_tree: Path) -> WheelContents:
        """Enumerate the agent files and skill dirs present in a wheel tree."""
        agents_dir = wheel_tree / "nWave" / "agents"
        skills_dir = wheel_tree / "nWave" / "skills"
        agent_files = (
            frozenset(p.name for p in agents_dir.glob("nw-*.md"))
            if agents_dir.exists()
            else frozenset()
        )
        skill_dirs = (
            frozenset(
                p.name
                for p in skills_dir.iterdir()
                if p.is_dir() and p.name.startswith("nw-")
            )
            if skills_dir.exists()
            else frozenset()
        )
        return WheelContents(agent_files=agent_files, skill_dirs=skill_dirs)

    def verify_wheel_privacy(self, wheel_tree: Path) -> list[str]:
        """Run the wheel-privacy gate (RCA Fix 1 hardening).

        Delegates to the production ``verify_wheel_privacy`` port. Returns
        the list of privacy violations (empty == clean wheel).

        This port DOES NOT EXIST on master — its RED scaffold lives at
        ``scripts/release/verify_wheel_privacy.py``.
        """
        from scripts.release.verify_wheel_privacy import verify

        return verify(wheel_tree)

    def build_wheel_tree_with_corrupt_catalog(self, dest: Path) -> Path:
        """Build a clean wheel tree, then corrupt its framework-catalog.yaml.

        C6a fail-closed contract: the privacy gate consults the catalog as
        the public allow-list. If the catalog is unparseable, the gate
        cannot prove the wheel is clean, so it MUST refuse — never silently
        pass. Returns the tree with a malformed catalog.
        """
        target = self.build_stripped_wheel_tree(dest)
        catalog = target / "nWave" / "framework-catalog.yaml"
        catalog.write_text("agents: {[: broken yaml :]}\n", encoding="utf-8")
        return target

    def build_wheel_tree_with_missing_catalog(self, dest: Path) -> Path:
        """Build a clean wheel tree, then delete its framework-catalog.yaml.

        C6a fail-closed contract: a missing catalog is as untrustworthy as
        a corrupt one — the gate cannot enumerate the allow-list, so it
        MUST refuse. Returns the tree with no catalog.
        """
        target = self.build_stripped_wheel_tree(dest)
        catalog = target / "nWave" / "framework-catalog.yaml"
        if catalog.exists():
            catalog.unlink()
        return target


# ---------------------------------------------------------------------------
# Service 2 — install-log hygiene (concern 3)
# ---------------------------------------------------------------------------


class _CapturingLogger:
    """Minimal logger double capturing ``info`` lines (output-capture fake).

    External/non-deterministic port per the Architecture of Reference —
    the logger is faked so a Then-step can observe stdout.
    """

    def __init__(self) -> None:
        self.lines: list[str] = []

    def info(self, message: str) -> None:
        self.lines.append(message)

    # SkillsPlugin only calls .info during skill install; tolerate the rest.
    def __getattr__(self, _name: str):  # pragma: no cover - defensive
        return lambda *a, **k: None


class InstallLogService:
    """Runs the real installer ``SkillsPlugin`` and captures its log.

    SSOT for "what the installer prints". Uses the production
    ``SkillsPlugin`` + ``InstallContext`` (Pillar 3 — app as in
    production); only the logger is a capturing fake.
    """

    def __init__(self, source_repo_root: Path) -> None:
        self._source = source_repo_root

    def run_skill_install(self, mode: InstallMode, claude_dir: Path) -> InstallLog:
        """Install skills via the production plugin and return the log.

        ``mode`` selects DEV (per-skill diagnostics allowed) or PUBLIC
        (aggregate count only — no private identifiers).
        """
        from scripts.install.plugins.base import InstallContext
        from scripts.install.plugins.skills_plugin import SkillsPlugin

        logger = _CapturingLogger()
        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=self._source / "scripts",
            templates_dir=self._source / "nWave" / "templates",
            logger=logger,
            project_root=self._source,
            framework_source=self._source / "nWave",
            dev_mode=(mode is InstallMode.DEV),
        )
        (claude_dir / "skills").mkdir(parents=True, exist_ok=True)
        SkillsPlugin().install(context)

        skipped = sum(
            1 for ln in logger.lines if "non-public skill" in ln or "Skipped" in ln
        )
        return InstallLog(lines=tuple(logger.lines), skipped_count=skipped)


# ---------------------------------------------------------------------------
# Service 3 — dangling-reference prevention validator (concern 4)
# ---------------------------------------------------------------------------


class SkillReferenceService:
    """Runs the skill-reference integrity validator (RCA Fix 3 prevention).

    SSOT for "does every skill referenced by a public artifact survive
    the strip". Delegates to the production validator port.

    This port DOES NOT EXIST on master — its RED scaffold lives at
    ``scripts/validation/validate_skill_references.py``.
    """

    # The negative scenario plants ONE removable skill referenced from an
    # EXISTING catalogued public agent. The agent survives the strip (it is
    # in framework-catalog.yaml); the skill is uncatalogued (owned by no
    # agent's frontmatter ``skills:`` list) so the ownership-only strip
    # drops it — leaving the surviving public agent with a dead reference.
    REFERRING_PUBLIC_AGENT = "nw-troubleshooter.md"
    PLANTED_REMOVABLE_SKILL = "nw-planted-removable-skill"

    def __init__(self, source_repo_root: Path) -> None:
        self._source = source_repo_root

    def find_dangling_references(self, nwave_dir: Path | None = None) -> list[str]:
        """Return public artifacts whose referenced skills would be stripped.

        Empty list == every public-artifact skill reference survives.

        Args:
            nwave_dir: the ``nWave/`` directory to scan. Defaults to the
                real repository tree; the negative scenario passes a
                planted fixture tree built by
                :meth:`build_source_with_dangling_referrer`.
        """
        from scripts.validation.validate_skill_references import check_references

        return check_references(nwave_dir or (self._source / "nWave"))

    def build_source_with_dangling_referrer(self, dest: Path) -> Path:
        """Copy ``nWave/`` into *dest* and plant a real dangling referrer.

        The planted precondition:

          * a removable skill ``nw-planted-removable-skill`` — a real
            ``SKILL.md`` directory owned by no public agent's ``skills:``
            frontmatter, so the ownership-only strip drops it as orphan;
          * a body reference to that skill appended to an EXISTING
            catalogued public agent (``nw-troubleshooter``) — the agent
            survives the strip, so after the strip it carries a dead
            reference.

        Returns the planted ``nWave/`` directory for the guard to scan.
        """
        from scripts.release.strip_private_agents import strip

        target = dest / "dangling-source-tree"
        shutil.copytree(self._source / "nWave", target / "nWave", dirs_exist_ok=True)
        nwave = target / "nWave"

        skill_dir = nwave / "skills" / self.PLANTED_REMOVABLE_SKILL
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: nw-planted-removable-skill\n---\n"
            "# Planted removable skill\n"
            "Owned by no public agent — the strip drops this as orphan work.\n",
            encoding="utf-8",
        )

        agent_file = nwave / "agents" / self.REFERRING_PUBLIC_AGENT
        agent_file.write_text(
            agent_file.read_text(encoding="utf-8")
            + "\n## Planted reference\n"
            + f"Load `skills/{self.PLANTED_REMOVABLE_SKILL}/SKILL.md` "
            + "before proceeding.\n",
            encoding="utf-8",
        )

        # Sanity: the strip must keep the referring agent yet remove the
        # planted skill — proving the precondition is a genuine dangler.
        probe = dest / "strip-probe"
        shutil.copytree(nwave, probe / "nWave", dirs_exist_ok=True)
        strip(probe)
        assert (probe / "nWave" / "agents" / self.REFERRING_PUBLIC_AGENT).exists(), (
            "referring public agent must survive the strip"
        )
        assert not (
            probe / "nWave" / "skills" / self.PLANTED_REMOVABLE_SKILL
        ).exists(), "planted skill must be removed by the strip to be dangling"

        return nwave


# ---------------------------------------------------------------------------
# Composition root
# ---------------------------------------------------------------------------


@dataclass
class PrivacyLeakComposition:
    """Production composition root for the private-skill-leak suite.

    Wires the three services over the real repository tree. Tier A only —
    this is a config-shaped bugfix, no Tier B state machine.

    The release-pipeline strip-order concern is NOT served by a YAML-shape
    service here: testing the workflow's step layout couples the AT to an
    implementation shape (a standalone strip step) the shipped fix
    deliberately does not have — ``patch_pyproject.py`` strips in-process.
    The genuine outcome guard is the slice-01 walking skeleton
    (``tests/e2e/test_wheel_private_artifact_contract.py``), which builds
    the real ``.whl`` through the release pipeline and inspects the
    archive a customer actually receives.
    """

    repo_root: Path
    wheel: WheelBuildService = field(init=False)
    install_log: InstallLogService = field(init=False)
    references: SkillReferenceService = field(init=False)

    def __post_init__(self) -> None:
        self.wheel = WheelBuildService(self.repo_root)
        self.install_log = InstallLogService(self.repo_root)
        self.references = SkillReferenceService(self.repo_root)


def build_composition() -> PrivacyLeakComposition:
    """Production DI entry point — builds the composition over the real repo."""
    return PrivacyLeakComposition(repo_root=_REPO_ROOT)


# Re-export the canonical fixtures so the release-side ATs import one module.
__all__ = [
    "PRIVATE_AGENT_FILES",
    "PRIVATE_SKILL_DIRS",
    "InstallLog",
    "PrivacyLeakComposition",
    "SkillName",
    "WheelContents",
    "build_composition",
]
