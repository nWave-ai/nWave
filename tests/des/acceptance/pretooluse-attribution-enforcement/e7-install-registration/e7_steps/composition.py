"""Composition root for the E7 install-registration slice.

Two production-wired driving surfaces (Mandate 13 — driving-port-only, Layer 3
composition root over a sandboxed `~/.claude`):

  * `InstallComposition` drives the real `AttributionPlugin` install/uninstall
    lifecycle (the registration call site, Reuse row R7). It is the production
    plugin object (Pillar 3), wired to a sandboxed `~/.claude` + `~/.nwave` via a
    redirected `Path.home()` (precedent: `tests/des/unit/install/`
    `test_install_des_hooks.py`).

  * `CliComposition` drives the real `nwave-ai attribution on|off` handler (the
    post-install toggle, R7), the user-facing entry point for flipping the gate.

Both surfaces reach the SAME net-new production seam — the attribution-hook
registration that writes/removes the `Bash`/`pre-commit-attribution` entry in
`settings.json`, gated by `attribution.enabled`. Driving them through the real
install + CLI entry points (never the registration function in isolation) is the
Mandate-15 witnessing path: the seam is reached from the real entry points and
asserted on its observable effect (the settings.json `hooks.PreToolUse` content).

The single observable across every scenario is `SettingsView` — a read-only
projection of `~/.claude/settings.json hooks.PreToolUse`. Business logic
(reading settings, counting entries, classifying coexistence) lives here as the
single source of truth; step bodies delegate and never inline logic
(Mandate-12 criterion 3).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .domain_types import (
    ATTRIBUTION_ACTION,
    GUARD_MARKER,
    OPERATOR_BASH_HOOK,
    AttributionChoice,
)


# ---------------------------------------------------------------------------
# The observable — a read-only projection of settings.json hooks.PreToolUse
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettingsView:
    """Read-only view of `~/.claude/settings.json hooks.PreToolUse`.

    All E7 outcomes are observable here: which Bash hook entries are registered.
    The view is rebuilt from disk after each driving-port invocation, so a Then
    step observes the real post-action settings.json content.
    """

    pre_tool_use_entries: tuple[dict, ...]
    raw_text: str | None

    @classmethod
    def read(cls, claude_dir: Path) -> SettingsView:
        """Project the live settings.json into the observable view."""
        settings_path = claude_dir / "settings.json"
        if not settings_path.exists():
            return cls(pre_tool_use_entries=(), raw_text=None)
        raw = settings_path.read_text(encoding="utf-8")
        try:
            config = json.loads(raw)
        except json.JSONDecodeError:
            return cls(pre_tool_use_entries=(), raw_text=raw)
        entries = config.get("hooks", {}).get("PreToolUse", [])
        return cls(pre_tool_use_entries=tuple(entries), raw_text=raw)

    @staticmethod
    def _entry_commands(entry: dict) -> list[str]:
        """All command strings inside one hooks.PreToolUse entry."""
        return [h.get("command", "") for h in entry.get("hooks", [])]

    def attribution_hook_count(self) -> int:
        """How many registered Bash entries route to the attribution action."""
        return sum(
            1
            for entry in self.pre_tool_use_entries
            if entry.get("matcher") == "Bash"
            and any(ATTRIBUTION_ACTION in cmd for cmd in self._entry_commands(entry))
        )

    def guard_is_registered(self) -> bool:
        """Whether the existing DES `pre-bash` execution-log guard is present."""
        return any(
            GUARD_MARKER in cmd
            for entry in self.pre_tool_use_entries
            for cmd in self._entry_commands(entry)
        )

    def operator_hook_is_registered(self) -> bool:
        """Whether the operator's own Bash hook survived registration."""
        operator_cmd = OPERATOR_BASH_HOOK["hooks"][0]["command"]
        return any(
            operator_cmd in cmd
            for entry in self.pre_tool_use_entries
            for cmd in self._entry_commands(entry)
        )


# ---------------------------------------------------------------------------
# Sandbox builder — a real ~/.claude / ~/.nwave under tmp_path
# ---------------------------------------------------------------------------


def _guard_entry() -> dict:
    """A settings.json entry standing in for the DES `pre-bash` guard.

    Carries the production marker substring so coexistence is asserted against
    real content, without re-running the full DES plugin install.
    """
    return {
        "matcher": "Bash",
        "hooks": [
            {"type": "command", "command": "# des-hook:pre-bash\nexit 0"},
        ],
    }


def write_settings(claude_dir: Path, config: dict) -> None:
    """Write a settings.json into the sandboxed Claude dir."""
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Surface 1 — install plugin lifecycle (real AttributionPlugin)
# ---------------------------------------------------------------------------


@dataclass
class InstallComposition:
    """Production-wired composition over the real `AttributionPlugin`.

    `home` is the sandboxed root; `claude_dir == home/.claude` and
    `config_dir == home/.nwave`. Tests redirect `Path.home()` to `home` so the
    plugin and its `attribution_utils` helpers resolve the sandbox.
    """

    home: Path

    @property
    def claude_dir(self) -> Path:
        return self.home / ".claude"

    @property
    def config_dir(self) -> Path:
        return self.home / ".nwave"

    def seed_guard(self) -> None:
        """Seed settings.json with the existing DES Bash guard (coexistence base)."""
        write_settings(self.claude_dir, {"hooks": {"PreToolUse": [_guard_entry()]}})

    def seed_operator_hook(self) -> None:
        """Append an operator-authored Bash hook the registration must preserve."""
        config = json.loads((self.claude_dir / "settings.json").read_text())
        config["hooks"]["PreToolUse"].append(OPERATOR_BASH_HOOK)
        write_settings(self.claude_dir, config)

    def seed_corrupt_settings(self) -> None:
        """Seed a corrupt (non-JSON) settings.json that must be left untouched."""
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        (self.claude_dir / "settings.json").write_text("{ not json", encoding="utf-8")

    def set_preference(self, choice: AttributionChoice) -> None:
        """Record the operator's attribution preference (the registration gate)."""
        from scripts.install.attribution_utils import write_attribution_preference

        write_attribution_preference(
            self.config_dir, enabled=choice is AttributionChoice.ENABLED
        )

    def _plugin(self):
        from scripts.install.plugins.attribution_plugin import AttributionPlugin

        return AttributionPlugin(config_dir=self.config_dir)

    def _context(self):
        from scripts.install.plugins.base import InstallContext

        project_root = Path(__file__).resolve().parents[6]
        return InstallContext(
            claude_dir=self.claude_dir,
            scripts_dir=project_root / "scripts" / "install",
            templates_dir=project_root / "nWave" / "templates",
            logger=logging.getLogger("test.e7.install"),
            project_root=project_root,
            framework_source=project_root / "nWave",
            dry_run=False,
        )

    def install(self) -> str:
        """Drive the real plugin install; return the result message (observable)."""
        return self._plugin().install(self._context()).message

    def uninstall(self) -> str:
        """Drive the real plugin uninstall; return the result message."""
        return self._plugin().uninstall(self._context()).message

    def settings(self) -> SettingsView:
        """Project the post-action settings.json into the observable view."""
        return SettingsView.read(self.claude_dir)


# ---------------------------------------------------------------------------
# Surface 2 — `nwave-ai attribution on|off` CLI handler
# ---------------------------------------------------------------------------


@dataclass
class CliComposition:
    """Production-wired composition over the real `attribution on|off` handler."""

    home: Path

    @property
    def claude_dir(self) -> Path:
        return self.home / ".claude"

    def turn(self, state: str) -> int:
        """Drive the real `attribution on|off` CLI handler; return its exit code."""
        from nwave_ai.cli import _handle_attribution

        return _handle_attribution([state])

    def settings(self) -> SettingsView:
        """Project the post-action settings.json into the observable view."""
        return SettingsView.read(self.claude_dir)
