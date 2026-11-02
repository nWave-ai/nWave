"""DoctorContext — parameterises filesystem roots for hermetic testing.

All doctor checks receive a DoctorContext instead of calling Path.home()
directly.  Tests inject a context pointing at tmp_path to achieve full
filesystem isolation without mocking.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from nwave_ai.platform.locations import NWaveLocations
from nwave_ai.platform.result import Failure
from scripts.install.install_utils import PathUtils


#: Sentinel marking "home_dir was not explicitly passed", so __post_init__
#: can tell the production default_factory call apart from an explicit
#: override. Compared by identity only, never touched on disk.
#:
#: Why this matters: the production entry point (from_defaults(), used by
#: `nwave-ai doctor`) must resolve claude_dir via PathUtils.get_claude_
#: config_dir(), which honors CLAUDE_CONFIG_DIR / --target (ADR-001) --
#: install/uninstall/attribution already resolve on this property, but
#: doctor previously always used home_dir / ".claude", silently diagnosing
#: the WRONG installation on a multi-profile machine or after a --target
#: install. But every doctor check test (tests/nwave_ai/doctor/**) injects
#: isolation via `DoctorContext(home_dir=tmp_path)`, relying on claude_dir
#: deriving from that explicit tmp_path -- honoring an ambient
#: CLAUDE_CONFIG_DIR there instead would break hermetic isolation and could
#: point a test at the real ~/.claude. The sentinel lets both contracts hold:
#: explicit home_dir wins (test isolation), CLAUDE_CONFIG_DIR wins only when
#: nothing was overridden (production default).
_HOME_DIR_UNSET = Path("__nwave_doctor_context_home_dir_unset__")


@dataclass(frozen=True)
class DoctorContext:
    """Immutable context holding filesystem roots for the doctor command.

    Attributes:
        home_dir: User home directory (defaults to Path.home()). Used only
            for the ~/.nwave global-config namespace, which is intentionally
            NOT tied to CLAUDE_CONFIG_DIR (a distinct, machine-scoped
            namespace by design).
        project_root: Current project directory whose activation is resolved
            (defaults to Path.cwd()). Read-only — the doctor never writes here.
        claude_dir: Claude configuration directory. Defaults to
            PathUtils.get_claude_config_dir() (honors CLAUDE_CONFIG_DIR) when
            home_dir is not explicitly overridden; derives from home_dir /
            ".claude" when it is (test isolation).
        settings_path: Claude settings file (claude_dir / "settings.json").
        global_config_path: nWave global config file (home_dir / ".nwave" /
            "config.json").
    """

    home_dir: Path = field(default_factory=lambda: _HOME_DIR_UNSET)
    project_root: Path = field(default_factory=Path.cwd)
    claude_dir: Path = field(init=False)
    settings_path: Path = field(init=False)
    global_config_path: Path = field(init=False)

    def __post_init__(self) -> None:
        overridden = self.home_dir is not _HOME_DIR_UNSET
        if overridden:
            # An explicit root is the hermetic-test seam and deliberately
            # overrides ambient selected-home variables.
            resolved_home = self.home_dir
        else:
            locations = NWaveLocations.resolve(
                home=Path.home(),
                repo_root=Path.cwd(),
                agents_home_override=os.environ.get("NWAVE_AGENTS_HOME") or None,
                claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR") or None,
                codex_config_override=os.environ.get("CODEX_HOME") or None,
            )
            resolved_home = (
                Path.home()
                if isinstance(locations, Failure)
                else locations.unwrap().agents_home
            )
        resolved_claude = (
            self.home_dir / ".claude"
            if overridden
            else PathUtils.get_claude_config_dir()
        )
        object.__setattr__(self, "home_dir", resolved_home)
        object.__setattr__(self, "claude_dir", resolved_claude)
        object.__setattr__(self, "settings_path", resolved_claude / "settings.json")
        object.__setattr__(
            self,
            "global_config_path",
            resolved_home / ".nwave" / "config.json",
        )

    @classmethod
    def from_defaults(cls) -> DoctorContext:
        """Return a DoctorContext with all default paths."""
        return cls()
