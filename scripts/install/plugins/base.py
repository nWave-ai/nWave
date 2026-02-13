"""
Base classes for the plugin system.

Defines InstallationPlugin interface, InstallContext for shared state,
and PluginResult for structured installation results.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PluginResult:
    """Result of plugin installation."""

    success: bool
    plugin_name: str
    message: str = ""
    errors: list[str] = field(default_factory=list)
    installed_files: list[Path] = field(default_factory=list)

    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.plugin_name}: {self.message}"
        return f"✗ {self.plugin_name}: {self.message}"


@dataclass
class InstallContext:
    """Shared context passed to all plugins during installation."""

    claude_dir: Path
    scripts_dir: Path
    templates_dir: Path
    logger: Any  # Logger instance
    project_root: Path = None
    framework_source: Path = None
    backup_manager: Any = None  # BackupManager instance
    installation_verifier: Any = None  # InstallationVerifier instance
    rich_logger: Any = None  # RichLogger instance
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class InstallationPlugin(ABC):
    """Base class for installation plugins.

    Plugins are modular components that handle installation of specific
    framework elements (agents, commands, templates, utilities, DES, etc.).

    Each plugin declares its dependencies and priority level, allowing the
    PluginRegistry to resolve execution order via topological sort.
    """

    def __init__(self, name: str, priority: int = 100):
        """Initialize plugin.

        Args:
            name: Unique plugin identifier
            priority: Execution priority (lower = earlier). Default 100.
        """
        self.name = name
        self.priority = priority
        self.dependencies: list[str] = []

    @abstractmethod
    def install(self, context: InstallContext) -> PluginResult:
        """Install this plugin's components.

        Args:
            context: Shared installation context with utilities and state

        Returns:
            PluginResult indicating success/failure and details
        """
        pass

    @abstractmethod
    def verify(self, context: InstallContext) -> PluginResult:
        """Verify plugin installation was successful.

        Args:
            context: Shared installation context

        Returns:
            PluginResult indicating verification success/failure
        """
        pass

    def get_dependencies(self) -> list[str]:
        """Return list of plugin names this plugin depends on.

        Dependencies must be resolved before this plugin can install.

        Returns:
            List of dependency plugin names
        """
        return self.dependencies

    def set_dependencies(self, deps: list[str]) -> None:
        """Set plugin dependencies.

        Args:
            deps: List of plugin names to depend on
        """
        self.dependencies = deps
