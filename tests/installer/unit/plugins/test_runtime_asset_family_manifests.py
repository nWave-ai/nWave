"""Runtime-asset family manifests — dry_run + idempotency + pre-record pins (slice-02).

Sentinel-routed gaps (docs/feature/installer-orphan-sweep/distill/
red-classification.md, slice-02 section):

- **C5a (HIGH, the v3.15.1 bug class)**: ``dry_run`` performs NO deletion and
  writes NO family record, for each NEW sweep family (templates, utilities).
  Pinned by the dry-run arm of the contrast PBTs below — the full
  family-directory universe must be byte-identical across a dry run.
- **C4a (MEDIUM)**: applying each family's install twice yields the same
  state as applying it once (idempotency).
- **Pre-record templates-family fallback (MEDIUM)**: a 3.16.x-shaped
  templates dir (files on disk, no manifest) is ADOPTED — nothing foreign is
  deleted, the user is warned, records start being kept — the behavioral
  delta vs the retired source-diff sweep.

Driving ports at unit scope: ``TemplatesPlugin.install(InstallContext)`` and
``UtilitiesPlugin.install(InstallContext)`` (file precedent:
``test_des_scripts_manifest.py`` drives the des-scripts family). Real
filesystem under a per-example temp dir; the diagnostics logger is the only
substituted port.

State-delta paradigm (Gate 12): multi-slot filesystem mutation (asset files +
manifest document) — universe declared, implicit-unchanged fail-closed. The
sibling-key slot ``manifest.scripts_family`` carries no predicate on the real
arm: implicit-unchanged pins the merge semantics (a family rewrite must never
clobber a sibling family's record).
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st
from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.templates_plugin import TemplatesPlugin
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin
from scripts.shared.skill_distribution import read_manifest


_MANIFEST_FILE = ".nwave-manifest.json"
_TEMPLATES_KEY = "installed_templates"
_UTILITIES_KEY = "installed_utilities"
_SCRIPTS_KEY = "installed_scripts"
_LEGACY_DEFAULT_KEY = "installed_skills"  # the v1.0 single-family default

_PRE_EXISTING_CONTENT_PREFIX = "# pre-existing "

# -- templates family fixtures ------------------------------------------------

_TEMPLATE_SOURCE_FILES = ["current-template.yaml", "team-guide.md"]
_TEMPLATE_SOURCE_DIRS = ["schemas"]
_TEMPLATE_SOURCE_CONTENT = "# shipped by the current version\n"
_RETIRED_TEMPLATE_FILES = ["old-workflow-template.yaml"]
_RETIRED_TEMPLATE_DIRS = ["legacy-flavors"]
_USER_TEMPLATE_POOL = ["my-team-conventions.md"]

# -- utilities family fixtures ------------------------------------------------

_UTILITY_SCRIPTS = ["install_nwave_target_hooks.py", "validate_step_file.py"]
_UTILITY_SOURCE_CONTENT = '__version__ = "99.0.0"\n'
_RETIRED_UTILITY_POOL = ["legacy_migration_helper.py", "old_tool.py"]
_PERSONAL_SCRIPT_POOL = ["my_backup_tool.py", "team_helper.py"]
_DES_SCRIPT_NAMES = ["check_stale_phases.py", "scope_boundary_check.py"]


def _write_doc(target_dir: Path, doc: dict) -> None:
    """Fabricate a prior-version manifest document (test seeding only)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / _MANIFEST_FILE).write_text(json.dumps(doc, indent=2) + "\n")


def _tracked_union(target_dir: Path) -> frozenset[str] | None:
    """All names any record in the manifest document tracks (or None)."""
    manifest = read_manifest(target_dir)
    if manifest is None:
        return None
    return frozenset(
        name
        for value in manifest.values()
        if isinstance(value, list)
        for name in value
        if isinstance(name, str)
    )


def _family_names(target_dir: Path, key: str) -> tuple[str, ...] | None:
    manifest = read_manifest(target_dir) or {}
    value = manifest.get(key)
    if not isinstance(value, list):
        return None
    return tuple(value)


# =============================================================================
# Templates family
# =============================================================================


@dataclass(frozen=True)
class TemplatesPreState:
    """Shape of the target templates dir before the install runs."""

    era: str  # "never" | "pre-record" | "tracked"
    legacy_key_seed: bool  # tracked era: record under the v1.0 default key
    retired_tracked: frozenset[str]
    retired_on_disk: frozenset[str]  # subset of retired_tracked
    user_items: frozenset[str]
    shipped_present: bool


@st.composite
def templates_pre_states(draw) -> TemplatesPreState:
    era = draw(st.sampled_from(["never", "pre-record", "tracked"]))
    if era == "never":
        return TemplatesPreState(
            era, False, frozenset(), frozenset(), frozenset(), False
        )
    pool = _RETIRED_TEMPLATE_FILES + _RETIRED_TEMPLATE_DIRS
    retired_tracked = frozenset(draw(st.sets(st.sampled_from(pool))))
    retired_on_disk = frozenset(name for name in retired_tracked if draw(st.booleans()))
    user_items = frozenset(draw(st.sets(st.sampled_from(_USER_TEMPLATE_POOL))))
    shipped_present = draw(st.booleans())
    legacy_key_seed = draw(st.booleans())
    return TemplatesPreState(
        era,
        legacy_key_seed,
        retired_tracked,
        retired_on_disk,
        user_items,
        shipped_present,
    )


def _all_template_source_names() -> frozenset[str]:
    return frozenset(_TEMPLATE_SOURCE_FILES) | frozenset(_TEMPLATE_SOURCE_DIRS)


def _seed_template_item(templates_dir: Path, name: str) -> None:
    if name in _RETIRED_TEMPLATE_DIRS or name in _TEMPLATE_SOURCE_DIRS:
        item_dir = templates_dir / name
        item_dir.mkdir(parents=True, exist_ok=True)
        (item_dir / "asset.json").write_text("{}\n")
        return
    (templates_dir / name).write_text(f"{_PRE_EXISTING_CONTENT_PREFIX}{name}\n")


def _seed_templates_target(templates_dir: Path, pre_state: TemplatesPreState) -> None:
    if pre_state.era == "never":
        return
    templates_dir.mkdir(parents=True)
    on_disk = set(pre_state.retired_on_disk) | set(pre_state.user_items)
    if pre_state.shipped_present:
        on_disk |= _all_template_source_names()
    for name in on_disk:
        _seed_template_item(templates_dir, name)
    if pre_state.era == "tracked":
        tracked = sorted(_all_template_source_names() | pre_state.retired_tracked)
        key = _LEGACY_DEFAULT_KEY if pre_state.legacy_key_seed else _TEMPLATES_KEY
        _write_doc(templates_dir, {key: tracked, "version": "1.0"})


def _make_templates_context(base: Path, *, dry_run: bool) -> InstallContext:
    source = base / "nWave"
    templates_source = source / "templates"
    templates_source.mkdir(parents=True)
    for name in _TEMPLATE_SOURCE_FILES:
        (templates_source / name).write_text(_TEMPLATE_SOURCE_CONTENT)
    for name in _TEMPLATE_SOURCE_DIRS:
        asset_dir = templates_source / name
        asset_dir.mkdir(parents=True)
        (asset_dir / "asset.json").write_text("{}\n")
    return InstallContext(
        claude_dir=base / ".claude",
        scripts_dir=base / "scripts",
        templates_dir=templates_source,
        logger=MagicMock(),
        project_root=base / "project",
        framework_source=source,
        dry_run=dry_run,
    )


_TEMPLATES_UNIVERSE = {
    "templates.entries",
    "templates.file_contents",
    "manifest.tracked",
}


def _templates_state(templates_dir: Path) -> dict[str, Any]:
    if not templates_dir.exists():
        items: list[Path] = []
    else:
        items = [p for p in templates_dir.iterdir() if p.name != _MANIFEST_FILE]
    return {
        "templates.entries": frozenset(p.name for p in items),
        "templates.file_contents": frozenset(
            (p.name, p.read_text()) for p in items if p.is_file()
        ),
        "manifest.tracked": _tracked_union(templates_dir),
    }


def _expected_template_entries(pre: dict[str, Any]) -> frozenset[str]:
    """Contract: current assets plus every entry no record positively tracks."""
    tracked = pre["manifest.tracked"]
    preserved = (
        pre["templates.entries"]
        if tracked is None
        else pre["templates.entries"] - tracked
    )
    return _all_template_source_names() | preserved


def _expected_template_contents(pre: dict[str, Any]) -> frozenset:
    current = {(name, _TEMPLATE_SOURCE_CONTENT) for name in _TEMPLATE_SOURCE_FILES}
    preserved_names = _expected_template_entries(pre) - _all_template_source_names()
    preserved = {
        (name, content)
        for name, content in pre["templates.file_contents"]
        if name in preserved_names
    }
    return frozenset(current | preserved)


@given(pre_state=templates_pre_states())
@h_settings(max_examples=30, deadline=None)
def test_templates_mutation_happens_exactly_when_not_dry_run(
    pre_state: TemplatesPreState,
) -> None:
    """C5a: dry_run mutates NOTHING; a real run sweeps tracked-retired only."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Arm 1 — dry run: the whole universe is implicit-unchanged.
        dry_context = _make_templates_context(base / "dry", dry_run=True)
        dry_templates = dry_context.claude_dir / "templates"
        _seed_templates_target(dry_templates, pre_state)
        before_dry = _templates_state(dry_templates)
        dry_result = TemplatesPlugin().install(dry_context)
        assert dry_result.success, dry_result.message
        assert_state_delta(
            before=before_dry,
            after=_templates_state(dry_templates),
            universe=_TEMPLATES_UNIVERSE,
            expected={},  # no delete, no copy, no record write
        )

        # Arm 2 — real run from the SAME pre-state: the contract delta holds.
        real_context = _make_templates_context(base / "real", dry_run=False)
        real_templates = real_context.claude_dir / "templates"
        _seed_templates_target(real_templates, pre_state)
        before_real = _templates_state(real_templates)
        real_result = TemplatesPlugin().install(real_context)
        assert real_result.success, real_result.message
        assert_state_delta(
            before=before_real,
            after=_templates_state(real_templates),
            universe=_TEMPLATES_UNIVERSE,
            expected={
                "templates.entries": set_to(_expected_template_entries(before_real)),
                "templates.file_contents": set_to(
                    _expected_template_contents(before_real)
                ),
                "manifest.tracked": set_to(_all_template_source_names()),
            },
        )


@given(pre_state=templates_pre_states())
@h_settings(max_examples=30, deadline=None)
def test_templates_install_applied_twice_yields_the_once_applied_state(
    pre_state: TemplatesPreState,
) -> None:
    """C4a: the templates install is idempotent — second apply changes nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        context = _make_templates_context(base, dry_run=False)
        templates_dir = context.claude_dir / "templates"
        _seed_templates_target(templates_dir, pre_state)

        first_result = TemplatesPlugin().install(context)
        assert first_result.success, first_result.message
        after_first = _templates_state(templates_dir)
        # The once-applied state already satisfies the record contract
        # (also makes this pin RED before the family record exists).
        assert after_first["manifest.tracked"] == _all_template_source_names(), (
            "first apply must leave the family record tracking the shipped assets"
        )

        second_result = TemplatesPlugin().install(context)
        assert second_result.success, second_result.message
        assert_state_delta(
            before=after_first,
            after=_templates_state(templates_dir),
            universe=_TEMPLATES_UNIVERSE,
            expected={},  # idempotent: second apply is a no-op on the universe
        )


def test_pre_record_templates_dir_is_adopted_preserved_and_warned() -> None:
    """Pre-record fallback: a 3.16.x-shaped templates dir is adopted, not swept.

    Behavioral delta vs the retired source-diff sweep: foreign files survive
    with content, the user is warned about them, and a family record starts
    being kept (shipped names adopted).
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        context = _make_templates_context(base, dry_run=False)
        templates_dir = context.claude_dir / "templates"
        templates_dir.mkdir(parents=True)
        foreign = "old-workflow-template.yaml"
        user_file = "my-team-conventions.md"
        for name in (foreign, user_file):
            (templates_dir / name).write_text(f"{_PRE_EXISTING_CONTENT_PREFIX}{name}\n")

        result = TemplatesPlugin().install(context)

        assert result.success, result.message
        for name in (foreign, user_file):
            survivor = templates_dir / name
            assert survivor.exists(), (
                f"{name!r} was deleted on a pre-record upgrade — "
                f"preserve-by-default is a hard contract"
            )
            assert survivor.read_text() == f"{_PRE_EXISTING_CONTENT_PREFIX}{name}\n"
        warnings = [str(call) for call in context.logger.warning.call_args_list]
        assert any("preserv" in text.lower() for text in warnings), (
            f"no preserve warning surfaced for the unrecorded files — "
            f"the user must be told, not left guessing (warnings: {warnings})"
        )
        assert _family_names(templates_dir, _TEMPLATES_KEY) == tuple(
            sorted(_all_template_source_names())
        ), "adoption must start keeping records: shipped names tracked going forward"


# =============================================================================
# Utilities family
# =============================================================================


@dataclass(frozen=True)
class UtilitiesPreState:
    """Shape of the target scripts dir before the utilities install runs."""

    era: str  # "never" | "pre-record" | "tracked"
    retired_tracked: frozenset[str]
    retired_on_disk: frozenset[str]  # subset of retired_tracked
    personal: frozenset[str]
    shipped_present: bool
    sibling_recorded: bool  # DES family record present in the shared document


@st.composite
def utilities_pre_states(draw) -> UtilitiesPreState:
    era = draw(st.sampled_from(["never", "pre-record", "tracked"]))
    if era == "never":
        return UtilitiesPreState(
            era, frozenset(), frozenset(), frozenset(), False, False
        )
    retired_tracked = frozenset(draw(st.sets(st.sampled_from(_RETIRED_UTILITY_POOL))))
    retired_on_disk = frozenset(name for name in retired_tracked if draw(st.booleans()))
    personal = frozenset(draw(st.sets(st.sampled_from(_PERSONAL_SCRIPT_POOL))))
    shipped_present = draw(st.booleans())
    sibling_recorded = draw(st.booleans())
    return UtilitiesPreState(
        era,
        retired_tracked,
        retired_on_disk,
        personal,
        shipped_present,
        sibling_recorded,
    )


def _seed_utilities_target(scripts_dir: Path, pre_state: UtilitiesPreState) -> None:
    if pre_state.era == "never":
        return
    scripts_dir.mkdir(parents=True)
    on_disk = set(pre_state.retired_on_disk) | set(pre_state.personal)
    if pre_state.shipped_present:
        on_disk |= set(_UTILITY_SCRIPTS)
    if pre_state.sibling_recorded:
        on_disk |= set(_DES_SCRIPT_NAMES)
    for name in on_disk:
        (scripts_dir / name).write_text(f"{_PRE_EXISTING_CONTENT_PREFIX}{name}\n")
    doc: dict[str, Any] = {"version": "1.0"}
    if pre_state.sibling_recorded:
        doc[_SCRIPTS_KEY] = sorted(_DES_SCRIPT_NAMES)
    if pre_state.era == "tracked":
        doc[_UTILITIES_KEY] = sorted(set(_UTILITY_SCRIPTS) | pre_state.retired_tracked)
    if pre_state.sibling_recorded or pre_state.era == "tracked":
        _write_doc(scripts_dir, doc)


def _make_utilities_context(base: Path, *, dry_run: bool) -> InstallContext:
    source = base / "nWave"
    source_scripts = source / "scripts"
    source_scripts.mkdir(parents=True)
    for name in _UTILITY_SCRIPTS:
        (source_scripts / name).write_text(_UTILITY_SOURCE_CONTENT)
    return InstallContext(
        claude_dir=base / ".claude",
        scripts_dir=base / "scripts",
        templates_dir=source / "templates",
        logger=MagicMock(),
        project_root=base / "project",
        framework_source=source,
        dry_run=dry_run,
    )


_UTILITIES_UNIVERSE = {
    "scripts.files",
    "scripts.contents",
    "manifest.utilities_family",
    "manifest.scripts_family",
}


def _utilities_state(scripts_dir: Path) -> dict[str, Any]:
    if not scripts_dir.exists():
        files: list[Path] = []
    else:
        files = [p for p in scripts_dir.iterdir() if p.name != _MANIFEST_FILE]
    return {
        "scripts.files": frozenset(p.name for p in files),
        "scripts.contents": frozenset((p.name, p.read_text()) for p in files),
        "manifest.utilities_family": _family_names(scripts_dir, _UTILITIES_KEY),
        "manifest.scripts_family": _family_names(scripts_dir, _SCRIPTS_KEY),
    }


def _expected_utility_files(pre: dict[str, Any]) -> frozenset[str]:
    """Contract: current scripts plus every file the family record does not track."""
    own_tracked = pre["manifest.utilities_family"]
    if own_tracked is None:
        preserved = pre["scripts.files"]
    else:
        preserved = pre["scripts.files"] - frozenset(own_tracked)
    return frozenset(_UTILITY_SCRIPTS) | preserved


def _expected_utility_contents(pre: dict[str, Any]) -> frozenset:
    current = {(name, _UTILITY_SOURCE_CONTENT) for name in _UTILITY_SCRIPTS}
    preserved_names = _expected_utility_files(pre) - set(_UTILITY_SCRIPTS)
    preserved = {
        (name, content)
        for name, content in pre["scripts.contents"]
        if name in preserved_names
    }
    return frozenset(current | preserved)


@given(pre_state=utilities_pre_states())
@h_settings(max_examples=30, deadline=None)
def test_utilities_mutation_happens_exactly_when_not_dry_run(
    pre_state: UtilitiesPreState,
) -> None:
    """C5a: dry_run mutates NOTHING; a real run sweeps only its own record.

    ``manifest.scripts_family`` carries no predicate on the real arm:
    implicit-unchanged pins the merge semantics — the utilities rewrite must
    never clobber the DES family's record in the shared document.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Arm 1 — dry run: the whole universe is implicit-unchanged.
        dry_context = _make_utilities_context(base / "dry", dry_run=True)
        dry_scripts = dry_context.claude_dir / "scripts"
        _seed_utilities_target(dry_scripts, pre_state)
        before_dry = _utilities_state(dry_scripts)
        dry_result = UtilitiesPlugin().install(dry_context)
        assert dry_result.success, dry_result.message
        assert_state_delta(
            before=before_dry,
            after=_utilities_state(dry_scripts),
            universe=_UTILITIES_UNIVERSE,
            expected={},  # no delete, no copy, no record write
        )

        # Arm 2 — real run from the SAME pre-state: the contract delta holds.
        real_context = _make_utilities_context(base / "real", dry_run=False)
        real_scripts = real_context.claude_dir / "scripts"
        _seed_utilities_target(real_scripts, pre_state)
        before_real = _utilities_state(real_scripts)
        real_result = UtilitiesPlugin().install(real_context)
        assert real_result.success, real_result.message
        assert_state_delta(
            before=before_real,
            after=_utilities_state(real_scripts),
            universe=_UTILITIES_UNIVERSE,
            expected={
                "scripts.files": set_to(_expected_utility_files(before_real)),
                "scripts.contents": set_to(_expected_utility_contents(before_real)),
                "manifest.utilities_family": set_to(tuple(sorted(_UTILITY_SCRIPTS))),
            },
        )


@given(pre_state=utilities_pre_states())
@h_settings(max_examples=30, deadline=None)
def test_utilities_install_applied_twice_yields_the_once_applied_state(
    pre_state: UtilitiesPreState,
) -> None:
    """C4a: the utilities install is idempotent — second apply changes nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        context = _make_utilities_context(base, dry_run=False)
        scripts_dir = context.claude_dir / "scripts"
        _seed_utilities_target(scripts_dir, pre_state)

        first_result = UtilitiesPlugin().install(context)
        assert first_result.success, first_result.message
        after_first = _utilities_state(scripts_dir)
        # The once-applied state already satisfies the record contract
        # (also makes this pin RED before the family record exists).
        assert after_first["manifest.utilities_family"] == tuple(
            sorted(_UTILITY_SCRIPTS)
        ), "first apply must leave the family record tracking the shipped scripts"

        second_result = UtilitiesPlugin().install(context)
        assert second_result.success, second_result.message
        assert_state_delta(
            before=after_first,
            after=_utilities_state(scripts_dir),
            universe=_UTILITIES_UNIVERSE,
            expected={},  # idempotent: second apply is a no-op on the universe
        )
