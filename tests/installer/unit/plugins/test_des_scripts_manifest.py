"""DES scripts manifest sweep — dry_run + idempotency pinning (slice-01).

Sentinel-routed gaps (docs/feature/installer-orphan-sweep/distill/
red-classification.md):

- **C5a (HIGH, the v3.15.1 bug class)**: ``dry_run`` performs NO deletion and
  writes NO manifest. Pinned by the dry-run arm of the contrast PBT below —
  the full scripts-dir universe must be byte-identical across a dry run.
- **C4a (MEDIUM)**: applying the scripts install twice yields the same state
  as applying it once (idempotency).

Driving port at unit scope: ``DESPlugin._install_des_scripts(InstallContext)``
(file precedent: ``test_des_shim_installation.py`` drives
``_install_des_shims``). Real filesystem under a per-example temp dir; the
diagnostics logger is the only substituted port.

State-delta paradigm (Gate 12): multi-slot filesystem mutation (script files +
manifest document) — universe declared, implicit-unchanged fail-closed.
"""

from __future__ import annotations

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
from scripts.install.plugins.des_plugin import DESPlugin
from scripts.shared.skill_distribution import read_manifest, write_manifest


_CURRENT_SOURCE_CONTENT = "#!/usr/bin/env python3\n# current version\n"
_PRE_EXISTING_CONTENT_PREFIX = "# pre-existing "

_RETIRED_POOL = ["retired_helper.py", "old_gate_check.py", "legacy_probe.py"]
_PERSONAL_POOL = ["my_backup_tool.py", "team_helper.py"]

_UNIVERSE = {"scripts.files", "scripts.contents", "manifest.tracked_names"}


@dataclass(frozen=True)
class PreState:
    """Shape of the target scripts dir before the install runs."""

    era: str  # "never" | "pre-manifest" | "manifest-tracked"
    retired_tracked: frozenset[str]
    retired_on_disk: frozenset[str]  # subset of retired_tracked
    personal: frozenset[str]
    shipped_present: bool


@st.composite
def pre_states(draw) -> PreState:
    era = draw(st.sampled_from(["never", "pre-manifest", "manifest-tracked"]))
    if era == "never":
        return PreState(era, frozenset(), frozenset(), frozenset(), False)
    retired_tracked = frozenset(draw(st.sets(st.sampled_from(_RETIRED_POOL))))
    retired_on_disk = frozenset(name for name in retired_tracked if draw(st.booleans()))
    personal = frozenset(draw(st.sets(st.sampled_from(_PERSONAL_POOL))))
    shipped_present = draw(st.booleans())
    return PreState(era, retired_tracked, retired_on_disk, personal, shipped_present)


def _seed_target(scripts_dir: Path, pre_state: PreState) -> None:
    """Lay down the pre-existing target installation per the declared era."""
    if pre_state.era == "never":
        return
    scripts_dir.mkdir(parents=True)
    on_disk = set(pre_state.retired_on_disk) | set(pre_state.personal)
    if pre_state.shipped_present:
        on_disk |= set(DESPlugin.DES_SCRIPTS)
    for name in on_disk:
        (scripts_dir / name).write_text(f"{_PRE_EXISTING_CONTENT_PREFIX}{name}\n")
    if pre_state.era == "manifest-tracked":
        tracked = sorted(set(DESPlugin.DES_SCRIPTS) | pre_state.retired_tracked)
        write_manifest(scripts_dir, tracked)  # previous version's v1.0 shape


def _make_context(base: Path, *, dry_run: bool) -> InstallContext:
    """Minimal InstallContext with a fabricated current-version source tree."""
    source = base / "nWave"
    des_scripts = source / "scripts" / "des"
    des_scripts.mkdir(parents=True)
    for script in DESPlugin.DES_SCRIPTS:
        (des_scripts / script).write_text(_CURRENT_SOURCE_CONTENT)
    return InstallContext(
        claude_dir=base / ".claude",
        scripts_dir=base / "scripts",
        templates_dir=source / "templates",
        logger=MagicMock(),
        project_root=base / "project",
        framework_source=source,
        dry_run=dry_run,
    )


def _tracked_names(manifest: dict | None) -> frozenset[str] | None:
    """Names tracked by a v1.0-shaped manifest document, key-name agnostic."""
    if manifest is None:
        return None
    return frozenset(
        name for value in manifest.values() if isinstance(value, list) for name in value
    )


def _scripts_state(scripts_dir: Path) -> dict[str, Any]:
    """Capture the full observable universe of the target scripts dir."""
    if not scripts_dir.exists():
        files: list[Path] = []
    else:
        files = [p for p in scripts_dir.iterdir() if not p.name.startswith(".")]
    return {
        "scripts.files": frozenset(p.name for p in files),
        "scripts.contents": frozenset((p.name, p.read_text()) for p in files),
        "manifest.tracked_names": _tracked_names(read_manifest(scripts_dir)),
    }


def _expected_files_after_real_install(pre: dict[str, Any]) -> frozenset[str]:
    """Contract: current scripts plus every file no manifest positively tracks."""
    tracked = pre["manifest.tracked_names"]
    preserved = (
        pre["scripts.files"] if tracked is None else pre["scripts.files"] - tracked
    )
    return frozenset(DESPlugin.DES_SCRIPTS) | preserved


def _expected_contents_after_real_install(pre: dict[str, Any]) -> frozenset:
    current = {(name, _CURRENT_SOURCE_CONTENT) for name in DESPlugin.DES_SCRIPTS}
    preserved_names = _expected_files_after_real_install(pre) - set(
        DESPlugin.DES_SCRIPTS
    )
    preserved = {
        (name, content)
        for name, content in pre["scripts.contents"]
        if name in preserved_names
    }
    return frozenset(current | preserved)


@given(pre_state=pre_states())
@h_settings(max_examples=30, deadline=None)
def test_deletion_and_manifest_write_happen_exactly_when_not_dry_run(
    pre_state: PreState,
) -> None:
    """C5a: dry_run mutates NOTHING; a real run sweeps + writes the manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Arm 1 — dry run: the whole universe is implicit-unchanged.
        dry_context = _make_context(base / "dry", dry_run=True)
        dry_scripts = dry_context.claude_dir / "scripts"
        _seed_target(dry_scripts, pre_state)
        before_dry = _scripts_state(dry_scripts)
        dry_result = DESPlugin()._install_des_scripts(dry_context)
        assert dry_result.success, dry_result.message
        assert_state_delta(
            before=before_dry,
            after=_scripts_state(dry_scripts),
            universe=_UNIVERSE,
            expected={},  # every slot implicit-unchanged: no delete, no write
        )

        # Arm 2 — real run from the SAME pre-state: the contract delta holds.
        real_context = _make_context(base / "real", dry_run=False)
        real_scripts = real_context.claude_dir / "scripts"
        _seed_target(real_scripts, pre_state)
        before_real = _scripts_state(real_scripts)
        real_result = DESPlugin()._install_des_scripts(real_context)
        assert real_result.success, real_result.message
        assert_state_delta(
            before=before_real,
            after=_scripts_state(real_scripts),
            universe=_UNIVERSE,
            expected={
                "scripts.files": set_to(
                    _expected_files_after_real_install(before_real)
                ),
                "scripts.contents": set_to(
                    _expected_contents_after_real_install(before_real)
                ),
                "manifest.tracked_names": set_to(frozenset(DESPlugin.DES_SCRIPTS)),
            },
        )


@given(pre_state=pre_states())
@h_settings(max_examples=30, deadline=None)
def test_install_scripts_applied_twice_yields_the_once_applied_state(
    pre_state: PreState,
) -> None:
    """C4a: the scripts install is idempotent — second apply changes nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        context = _make_context(base, dry_run=False)
        scripts_dir = context.claude_dir / "scripts"
        _seed_target(scripts_dir, pre_state)

        first_result = DESPlugin()._install_des_scripts(context)
        assert first_result.success, first_result.message
        after_first = _scripts_state(scripts_dir)
        # The once-applied state already satisfies the manifest contract
        # (also makes this pin RED before the manifest behaviour exists).
        assert after_first["manifest.tracked_names"] == frozenset(
            DESPlugin.DES_SCRIPTS
        ), "first apply must leave the manifest tracking the installed scripts"

        second_result = DESPlugin()._install_des_scripts(context)
        assert second_result.success, second_result.message
        assert_state_delta(
            before=after_first,
            after=_scripts_state(scripts_dir),
            universe=_UNIVERSE,
            expected={},  # idempotent: second apply is a no-op on the universe
        )
