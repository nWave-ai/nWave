"""Regression: AttributionPlugin must route every settings-touching call to
context.claude_dir, not Path.home()/.claude.

Defect (split-brain): the plugin passed only ``self._config_dir`` positionally
to the settings-touching helpers, so ``claude_dir`` defaulted to
``Path.home()/.claude``. Under ``install --target <path>`` the managed payload
landed in ``~/.claude`` (wrong) instead of ``<path>`` — the two halves of the
same feature split across two directories. RCA:
docs/feature/fix-attribution-plugin-claude-dir/deliver/rca.md.

ADR-CA-007 reconciliation: the un-gateable ``settings.json attribution.{commit,pr}``
WRITE is retired; install now registers the activation-gated PreToolUse hook
(``register_attribution_hook(claude_dir=...)``) and records the opt-in
preference. The ``claude_dir`` injection seam is LOAD-BEARING and PRESERVED —
this regression still guards it, now over the hook-registration call site (the
surviving settings-touching surface) instead of the retired credit writer.
Uninstall still routes ``remove_settings_attribution`` through ``claude_dir``
(RETAINED legacy-block cleanup), so that half is unchanged.

These tests drive the REAL AttributionPlugin.install()/.uninstall() with NO
stubbing of the settings helpers — they live under tests/bugs/, which does NOT
inherit the module-scoped ``isolate_attribution_side_effects`` autouse fixture
from tests/installer/unit/plugins/test_attribution_plugin.py, so the real
settings read+write executes and the routing is observable.

This is a wiring/routing regression (verifies the plugin call sites forward
``context.claude_dir``): single-example by nature, EXEMPT from the PBT-default
mandate (mirrors test_milestone_2_uninstall_wiring.py).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from scripts.install.attribution_utils import (
    NWAVE_MANAGED_COMMIT,
    NWAVE_MANAGED_PR,
)
from scripts.install.plugins.attribution_plugin import AttributionPlugin
from scripts.install.plugins.base import InstallContext


def _make_context(claude_dir: Path, nwave_config_dir: Path) -> InstallContext:
    """Minimal InstallContext pointing claude_dir at the install target.

    Mirrors the shape of tests/installer/unit/plugins/test_attribution_plugin.py
    ::_make_context but is constructed directly so the autouse stub fixture in
    that module is NOT triggered.
    """
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=claude_dir.parent / "scripts",
        templates_dir=claude_dir.parent / "templates",
        logger=MagicMock(),
        project_root=claude_dir.parent / "project",
        metadata={"nwave_config_dir": nwave_config_dir},
    )


def _settings_attribution_commit(claude_dir: Path) -> object | None:
    """Return settings.json attribution.commit for claude_dir, or None."""
    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return None
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    return (settings.get("attribution") or {}).get("commit")


def _attribution_hook_registered(claude_dir: Path) -> bool:
    """Whether the CA-007 PreToolUse commit-attribution hook is in claude_dir."""
    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return False
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    entries = (settings.get("hooks") or {}).get("PreToolUse") or []
    return any(
        entry.get("matcher") == "Bash"
        and any(
            "pre-commit-attribution" in (hook.get("command") or "")
            for hook in entry.get("hooks") or []
        )
        for entry in entries
    )


def test_install_routes_attribution_hook_to_target_claude_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """install() registers the hook into ctx.claude_dir, not ~/.claude (CA-007).

    ADR-CA-007: the settings.json credit WRITE is retired, so the observable is
    the registered PreToolUse hook (the surviving settings-touching surface).
    The claude_dir injection seam must route it to the install target and leave
    the default ~/.claude untouched.
    """
    home = tmp_path / "home"
    home_claude = home / ".claude"
    home_claude.mkdir(parents=True)  # MUST exist or registration warn+skips
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    target_claude = tmp_path / "target_claude"
    target_claude.mkdir()  # exists AND differs from Path.home()/.claude

    nwave_config = tmp_path / ".nwave"
    ctx = _make_context(target_claude, nwave_config)

    AttributionPlugin(config_dir=nwave_config).install(ctx)

    # Hook registered into the install target (claude_dir seam preserved).
    assert _attribution_hook_registered(target_claude) is True
    # And did NOT pollute the default ~/.claude (the anti-assertion = the RED).
    assert _attribution_hook_registered(home_claude) is False
    # And NO settings.json attribution credit was written anywhere (retired).
    assert _settings_attribution_commit(target_claude) is None
    assert _settings_attribution_commit(home_claude) is None


def test_install_routes_legacy_migration_to_target_claude_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """install() routes the legacy-settings migration into ctx.claude_dir.

    ADR-CA-007 DDD-3: install now performs a one-shot
    ``migrate_legacy_settings_attribution`` cleanup of a previously nWave-written
    settings credit. The claude_dir injection seam must route that cleanup to the
    install target -- a legacy block seeded in the TARGET is removed, while the
    default ~/.claude is never read or written.
    """
    home = tmp_path / "home"
    home_claude = home / ".claude"
    home_claude.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    target_claude = tmp_path / "target_claude"
    target_claude.mkdir()

    nwave_config = tmp_path / ".nwave"

    # Seed a nWave-managed legacy credit into the TARGET settings.json, plus the
    # baseline so the classifier recognises it as nWave-managed.
    (target_claude / "settings.json").write_text(
        json.dumps(
            {"attribution": {"commit": NWAVE_MANAGED_COMMIT, "pr": NWAVE_MANAGED_PR}},
            indent=2,
        ),
        encoding="utf-8",
    )

    ctx = _make_context(target_claude, nwave_config)
    AttributionPlugin(config_dir=nwave_config).install(ctx)

    # Legacy credit removed from the install target (migration routed via seam).
    assert _settings_attribution_commit(target_claude) is None
    # And the default ~/.claude was never written.
    assert not (home_claude / "settings.json").exists()


def test_uninstall_removes_payload_from_target_claude_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """uninstall() removes the managed payload from ctx.claude_dir and leaves
    ~/.claude untouched."""
    home = tmp_path / "home"
    home_claude = home / ".claude"
    home_claude.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    target_claude = tmp_path / "target_claude"
    target_claude.mkdir()

    # Seed the managed payload into the TARGET settings.json.
    (target_claude / "settings.json").write_text(
        json.dumps(
            {"attribution": {"commit": NWAVE_MANAGED_COMMIT, "pr": NWAVE_MANAGED_PR}},
            indent=2,
        ),
        encoding="utf-8",
    )

    nwave_config = tmp_path / ".nwave"
    ctx = _make_context(target_claude, nwave_config)

    AttributionPlugin(config_dir=nwave_config).uninstall(ctx)

    # Managed payload removed from the install target.
    assert _settings_attribution_commit(target_claude) is None
    # And ~/.claude was never touched (no settings.json created there).
    assert not (home_claude / "settings.json").exists()
