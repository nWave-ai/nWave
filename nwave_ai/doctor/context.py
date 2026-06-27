"""DoctorContext — parameterises filesystem roots for hermetic testing.

All doctor checks receive a DoctorContext instead of calling Path.home()
directly.  Tests inject a context pointing at tmp_path to achieve full
filesystem isolation without mocking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DoctorContext:
    """Immutable context holding filesystem roots for the doctor command.

    Attributes:
        home_dir: User home directory (defaults to Path.home()).
        project_root: Current project directory whose activation is resolved
            (defaults to Path.cwd()). Read-only — the doctor never writes here.
        claude_dir: Claude configuration directory (defaults to home_dir / ".claude").
        settings_path: Claude settings file (defaults to claude_dir / "settings.json").
        global_config_path: nWave global config file (defaults to
            home_dir / ".nwave" / "global-config.json").
    """

    home_dir: Path = field(default_factory=Path.home)
    project_root: Path = field(default_factory=Path.cwd)
    claude_dir: Path = field(init=False)
    settings_path: Path = field(init=False)
    global_config_path: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "claude_dir", self.home_dir / ".claude")
        object.__setattr__(self, "settings_path", self.claude_dir / "settings.json")
        object.__setattr__(
            self,
            "global_config_path",
            self.home_dir / ".nwave" / "global-config.json",
        )

    @classmethod
    def from_defaults(cls) -> DoctorContext:
        """Return a DoctorContext with all default paths."""
        return cls()
