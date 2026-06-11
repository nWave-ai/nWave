"""Composition root for installer-orphan-sweep slice-03 acceptance tests.

Drives the REAL verification CLI entry the operator runs —
``scripts.install.verify_nwave.main(["--json"], claude_config_dir=...)`` —
against a fully-recorded installed target on a real filesystem under
``tmp_path`` (Driving-Port-Only Boundary mandate, Layer-3 composition on the
production CLI composition root; Pillar 3: nothing is faked — stdout is the
captured user surface). The same ``InstallationVerifier.run_verification()``
struct this entry renders also feeds the install summary
(``install_nwave.validate_installation``) — one seam, two consumers.

Oracle decision (pinned): MANIFEST-BASED. The expected set per family
directory is the union of the family records in that directory's shared
``.nwave-manifest.json`` (``installed_scripts`` / ``installed_utilities`` /
``installed_templates`` / ``installed_skills`` — the production SSOT slices
01/02 shipped). A source-based oracle is unsound here: the verifier runs
standalone on the target machine where no framework source exists, and a
second ship-list would fork the SSOT the manifests already are.

Report taxonomy (pinned, C2a — the three classes a disk entry can be in):

- ACCOUNTED      — tracked by some family record in the directory's
  manifest (or the manifest bookkeeping file itself): expected, not listed.
- UNACCOUNTED    — on disk, tracked by no record: listed INFORMATIONALLY,
  per family. The verifier cannot prove provenance (a user-created
  ``nw-custom`` skill and a pre-manifest framework orphan are
  indistinguishable by record membership — the skills preserve-rule
  precedent), so the listing means "preserved, not managed by nWave" and
  NEVER "delete these". Unaccounted files never fail verification.
- OUT OF SCOPE   — outside every family directory, or in a directory with
  no manifest (agents): invisible to the report.

Read-only BY CONTRACT: the verifier never mutates the tree. Pinned via the
universe — ``installation.tree_digest`` carries NO expected predicate, so any
created/modified/removed path under the target fails closed (Mandate 8). The
single honest exclusion is the diagnostics log ``nwave-install.log`` the
verification CLI appends to by design.

All slice business logic (seeding, report normalization, expected-delta
computation, universe capture) lives HERE as the single source of truth;
step bodies in ``test_verifier_orphan_report.py`` delegate one call each
(SSOT-via-Types-Services-DSL mandate, criterion 3).

Universe (Mandate 8, layer 3 — port-exposed observables only):

- ``report.exit_code``        — process exit code returned by the CLI entry
- ``report.success``          — the report's overall verdict field
- ``report.error_code``       — declared error code in the report, or None
- ``report.unaccounted``      — mapping family -> names listed as
  unaccounted (JSON field ``unaccounted_files``; empty families dropped;
  None when the report has no orphan visibility at all)
- ``report.problem_files``    — names the report classifies as problems
  (missing essential files), or None pre-run
- ``report.runs_identical``   — True when consecutive runs reported the
  same (idempotency witness); None on single-run journeys
- ``installation.tree_digest`` — (relpath, content-hash) pairs over the
  whole target tree minus the diagnostics log; implicit-unchanged,
  fail-closed in every scenario
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.installation_verifier import InstallationVerifier
from scripts.install.plugins.des_plugin import DESPlugin
from scripts.install.verify_nwave import main as verify_nwave_main
from scripts.shared.skill_distribution import (
    SCRIPTS_FAMILY_KEY,
    TEMPLATES_FAMILY_KEY,
    UTILITIES_FAMILY_KEY,
    write_family_record,
    write_manifest,
)

from .domain_types import (
    CURRENT_ASSET_DIR,
    UTILITY_SCRIPTS,
    AssetFamily,
    ScriptName,
    SkillName,
    TemplateName,
)


_UNIVERSE = {
    "report.exit_code",
    "report.success",
    "report.error_code",
    "report.unaccounted",
    "report.problem_files",
    "report.runs_identical",
    "installation.tree_digest",
}

#: The one file the verification CLI legitimately appends to (its diagnostics
#: log) — excluded BY NAME from the read-only universe; everything else is
#: implicit-unchanged, fail-closed.
_DIAGNOSTICS_LOG = "nwave-install.log"

#: The report's machine surface for the per-family unaccounted listing.
_REPORT_FIELD = "unaccounted_files"

_PERSONAL_SCRIPT_CONTENT = "# personal tool — the installer must never touch this\n"
_USER_TEMPLATE_CONTENT = (
    "# the team's own template — the installer must never touch this\n"
)
_USER_SKILL_CONTENT = "---\nname: nw-custom\nuser-invocable: true\n---\n\n# Mine\n"


class VerifierReportJourney:
    """One operator journey: a recorded installation, real verifier run(s)."""

    def __init__(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self._claude_dir = tmp_path / ".claude"
        self._claude_dir.mkdir(parents=True, exist_ok=True)
        self._scripts_target = self._claude_dir / "scripts"
        self._templates_target = self._claude_dir / "templates"
        self._skills_target = self._claude_dir / "skills"
        self._unaccounted_seeds: dict[AssetFamily, set[str]] = {
            family: set() for family in AssetFamily
        }
        self._user_assets: dict[AssetFamily, set[str]] = {
            family: set() for family in AssetFamily
        }
        self._runs = 0
        self._exit_code: int | None = None
        self._parsed: dict[str, Any] | None = None
        self._runs_identical: bool | None = None
        self._before: dict[str, Any] | None = None
        self._after: dict[str, Any] | None = None

    # -- Given services --------------------------------------------------------

    def given_recorded_installation(self) -> None:
        """The post-slice-01/02 state: every asset family on disk AND recorded.

        Seeds a verification-healthy target (essential skills, DES module,
        installation manifest) with every family record written through the
        SHARED production primitives — the exact on-disk contract the shipped
        slice-01/02 installer leaves behind.
        """
        # skills family — essential command-skills, recorded (v1.0 shape).
        skill_names = list(InstallationVerifier.ESSENTIAL_COMMAND_SKILLS)
        for name in skill_names:
            skill_dir = self._skills_target / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\nuser-invocable: true\n---\n\n# {name}\n"
            )
        write_manifest(self._skills_target, skill_names)
        # scripts directory — two families sharing one record document.
        self._scripts_target.mkdir(parents=True, exist_ok=True)
        for name in DESPlugin.DES_SCRIPTS:
            (self._scripts_target / name).write_text("#!/usr/bin/env python3\n")
        for name in UTILITY_SCRIPTS:
            (self._scripts_target / name).write_text('__version__ = "99.0.0"\n')
        write_family_record(
            self._scripts_target, list(DESPlugin.DES_SCRIPTS), key=SCRIPTS_FAMILY_KEY
        )
        write_family_record(
            self._scripts_target, list(UTILITY_SCRIPTS), key=UTILITIES_FAMILY_KEY
        )
        # runtime-assets family (templates directory), recorded.
        self._templates_target.mkdir(parents=True, exist_ok=True)
        asset_names: list[str] = []
        for name in DESPlugin.DES_TEMPLATES:
            (self._templates_target / name).write_text("# template\n")
            asset_names.append(name)
        current_asset = self._templates_target / CURRENT_ASSET_DIR
        current_asset.mkdir(parents=True, exist_ok=True)
        (current_asset / "asset.json").write_text("{}\n")
        asset_names.append(CURRENT_ASSET_DIR)
        write_family_record(
            self._templates_target, asset_names, key=TEMPLATES_FAMILY_KEY
        )
        # DES module + installation manifest — verification-healthy baseline.
        des_lib = self._claude_dir / "lib" / "python" / "des"
        des_lib.mkdir(parents=True, exist_ok=True)
        (des_lib / "__init__.py").write_text("")
        (self._claude_dir / "nwave-manifest.txt").write_text(
            "nWave installation manifest\n"
        )

    def given_unaccounted_scripts(self, names: tuple[ScriptName, ...]) -> None:
        """Stray scripts on disk that no family record tracks."""
        for name in names:
            (self._scripts_target / name).write_text("# stale leftover\n")
            self._unaccounted_seeds[AssetFamily.SCRIPTS].add(name)

    def given_unaccounted_asset_dir(self, name: TemplateName) -> None:
        """A stray runtime-asset folder on disk that no family record tracks."""
        stray = self._templates_target / name
        stray.mkdir(parents=True, exist_ok=True)
        (stray / "asset.json").write_text("{}\n")
        self._unaccounted_seeds[AssetFamily.RUNTIME_ASSETS].add(name)

    def given_personal_script(self, name: ScriptName) -> None:
        """A user-created script the framework never installed nor tracked."""
        (self._scripts_target / name).write_text(_PERSONAL_SCRIPT_CONTENT)
        self._user_assets[AssetFamily.SCRIPTS].add(name)
        self._unaccounted_seeds[AssetFamily.SCRIPTS].add(name)

    def given_user_template(self, name: TemplateName) -> None:
        """A user-created template the framework never installed nor tracked."""
        (self._templates_target / name).write_text(_USER_TEMPLATE_CONTENT)
        self._user_assets[AssetFamily.RUNTIME_ASSETS].add(name)
        self._unaccounted_seeds[AssetFamily.RUNTIME_ASSETS].add(name)

    def given_user_skill(self, name: SkillName) -> None:
        """A user-created nw-* skill — preserved by contract, tracked by nobody."""
        skill_dir = self._skills_target / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(_USER_SKILL_CONTENT)
        self._user_assets[AssetFamily.SKILLS].add(name)
        self._unaccounted_seeds[AssetFamily.SKILLS].add(name)

    # -- When service ------------------------------------------------------------

    def run_verifier(self, capsys: Any, runs: int = 1) -> None:
        """Drive the real driving port: the verification CLI entry, JSON surface."""
        self._before = self._capture_universe()
        capsys.readouterr()  # drain anything previously printed
        observed: list[tuple[int, dict[str, Any]]] = []
        for _ in range(runs):
            exit_code = verify_nwave_main(
                ["--json"], claude_config_dir=self._claude_dir
            )
            observed.append((exit_code, json.loads(capsys.readouterr().out)))
        self._runs = runs
        self._exit_code, self._parsed = observed[-1]
        self._runs_identical = (
            all(entry == observed[0] for entry in observed) if runs > 1 else None
        )
        self._after = self._capture_universe()

    # -- Then services -----------------------------------------------------------

    def assert_unaccounted_listed(
        self, family: AssetFamily, names: frozenset[str]
    ) -> None:
        listed = (self._after["report.unaccounted"] or {}).get(
            family.value, frozenset()
        )
        missing = names - listed
        assert not missing, (
            f"the report does not list {sorted(missing)} as unaccounted in the "
            f"{family.value!r} family — orphans are invisible to the operator "
            f"(listed: {sorted(listed)})"
        )

    def assert_clean_bill(self) -> None:
        assert self._after["report.unaccounted"] == {}, (
            "the report does not positively confirm that every file is "
            "accounted for — got "
            f"{self._after['report.unaccounted']!r} (None means the verifier "
            "has no orphan visibility at all)"
        )

    def assert_runs_identical(self) -> None:
        assert self._after["report.runs_identical"] is True, (
            "consecutive verifier runs did not report the same — a read-only "
            "report must be idempotent"
        )

    def assert_verification_passes(self) -> None:
        assert self._exit_code == 0 and self._after["report.success"] is True, (
            f"the verification did not pass (exit code {self._exit_code}, "
            f"success {self._after['report.success']!r}) — unaccounted files "
            f"are report-only and must never fail the verification"
        )

    def assert_user_assets_noted_as_preserved(self) -> None:
        for family, names in self._user_assets.items():
            if names:
                self.assert_unaccounted_listed(family, frozenset(names))

    def assert_user_assets_not_problems(self) -> None:
        user_names = {name for names in self._user_assets.values() for name in names}
        problems = self._after["report.problem_files"] or frozenset()
        assert (
            not (user_names & problems) and self._after["report.error_code"] is None
        ), (
            f"user-created assets were classified as problems — problems: "
            f"{sorted(problems)}, error code: "
            f"{self._after['report.error_code']!r}; preserve-by-default means "
            f"the report may note them as preserved, never as defects"
        )

    def assert_contract_holds(self) -> None:
        """Universe-bound contract: exactly the declared report, nothing touched."""
        assert_state_delta(
            before=self._before,
            after=self._after,
            universe=_UNIVERSE,
            expected=self._expected_delta(),
        )

    # -- internals ----------------------------------------------------------------

    def _expected_delta(self) -> dict[str, Any]:
        expected: dict[str, Any] = {
            "report.exit_code": set_to(0),
            "report.success": set_to(True),
            "report.error_code": set_to(None),
            "report.unaccounted": set_to(self._expected_unaccounted()),
            "report.problem_files": set_to(frozenset()),
        }
        if self._runs > 1:
            expected["report.runs_identical"] = set_to(True)
        # installation.tree_digest carries NO predicate: implicit-unchanged,
        # fail-closed (Mandate 8) — the verifier is read-only BY CONTRACT.
        return expected

    def _expected_unaccounted(self) -> dict[str, frozenset[str]]:
        return {
            family.value: frozenset(names)
            for family, names in self._unaccounted_seeds.items()
            if names
        }

    def _capture_universe(self) -> dict[str, Any]:
        parsed = self._parsed
        return {
            "report.exit_code": self._exit_code,
            "report.success": None if parsed is None else parsed.get("success"),
            "report.error_code": None if parsed is None else parsed.get("error_code"),
            "report.unaccounted": self._normalized_unaccounted(parsed),
            "report.problem_files": (
                None
                if parsed is None
                else frozenset(parsed.get("missing_essential_files") or [])
            ),
            "report.runs_identical": self._runs_identical,
            "installation.tree_digest": self._tree_digest(),
        }

    @staticmethod
    def _normalized_unaccounted(
        parsed: dict[str, Any] | None,
    ) -> dict[str, frozenset[str]] | None:
        """The per-family unaccounted listing; empty families dropped.

        ``None`` (field absent) is DISTINCT from ``{}`` (the report positively
        confirms every file is accounted for) — silence is not a clean bill.
        """
        if parsed is None or _REPORT_FIELD not in parsed:
            return None
        return {
            family: frozenset(names)
            for family, names in parsed[_REPORT_FIELD].items()
            if names
        }

    def _tree_digest(self) -> frozenset[tuple[str, str]]:
        """(relpath, content-hash) for the whole target tree minus the log."""
        entries: set[tuple[str, str]] = set()
        for path in self._claude_dir.rglob("*"):
            rel = path.relative_to(self._claude_dir).as_posix()
            if rel == _DIAGNOSTICS_LOG:
                continue
            if path.is_dir():
                entries.add((rel, "<dir>"))
            else:
                entries.add((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
        return frozenset(entries)
