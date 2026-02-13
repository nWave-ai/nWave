"""
Plugin registry with topological sort dependency resolution.

Uses Kahn's algorithm for topological sorting to determine plugin
execution order while respecting dependencies.

Includes rollback mechanism for handling plugin installation failures.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


if TYPE_CHECKING:
    from scripts.install.install_utils import Logger


class PluginRegistry:
    """Registry for managing plugins and their execution order.

    Uses topological sort (Kahn's algorithm) to resolve plugin dependencies
    and detect circular dependencies.

    Provides rollback mechanism to restore system state on installation failure.
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize empty plugin registry."""
        self.plugins: dict[str, InstallationPlugin] = {}
        self._installed_files: list[Path | str] = []
        self._installed_plugins: list[str] = []
        self._logger = logger

    def register(self, plugin: InstallationPlugin) -> None:
        """Register a plugin.

        Args:
            plugin: InstallationPlugin instance to register

        Raises:
            ValueError: If plugin with same name already registered
        """
        if plugin.name in self.plugins:
            raise ValueError(f"  🔩 Plugin '{plugin.name}' already registered")
        self.plugins[plugin.name] = plugin
        if self._logger:
            self._logger.info(f"  🪛 {plugin.name} added to the toolbox")

    def _detect_cycle_dfs(
        self,
        node: str,
        visited: set[str],
        rec_stack: set[str],
        graph: dict[str, list[str]],
    ) -> bool:
        """Detect cycle using depth-first search.

        Args:
            node: Current node being visited
            visited: Set of all visited nodes
            rec_stack: Set of nodes in current recursion stack
            graph: Adjacency list representation of dependencies

        Returns:
            True if cycle detected, False otherwise
        """
        visited.add(node)
        rec_stack.add(node)

        if node in graph:
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if self._detect_cycle_dfs(neighbor, visited, rec_stack, graph):
                        return True
                elif neighbor in rec_stack:
                    return True

        rec_stack.remove(node)
        return False

    def _topological_sort_kahn(self) -> list[str]:
        """Topological sort using Kahn's algorithm.

        Performs topological sort to determine plugin execution order
        while respecting dependencies.

        Returns:
            List of plugin names in execution order

        Raises:
            ValueError: If circular dependency detected or missing dependency
        """
        # Build adjacency list and in-degree count
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}

        for name in self.plugins:
            graph[name] = []
            in_degree[name] = 0

        for plugin in self.plugins.values():
            for dep in plugin.get_dependencies():
                if dep not in self.plugins:
                    raise ValueError(
                        f"Plugin '{plugin.name}' depends on missing plugin '{dep}'"
                    )
                graph[dep].append(plugin.name)
                in_degree[plugin.name] += 1

        # Collect nodes with no incoming edges
        queue = [name for name in self.plugins if in_degree[name] == 0]

        # Sort by priority for deterministic ordering when no dependencies
        queue.sort(key=lambda x: (in_degree[x], self.plugins[x].priority))

        sorted_order = []
        while queue:
            # Remove node with lowest priority (earliest execution)
            queue.sort(key=lambda x: self.plugins[x].priority)
            node = queue.pop(0)
            sorted_order.append(node)

            # For each neighbor
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check if all nodes are in sorted order (no cycle)
        if len(sorted_order) != len(self.plugins):
            raise ValueError("Circular dependency detected in plugins")

        return sorted_order

    def get_execution_order(self) -> list[str]:
        """Get plugin execution order respecting dependencies.

        Returns:
            List of plugin names in execution order

        Raises:
            ValueError: If circular dependency or missing dependency detected
        """
        return self._topological_sort_kahn()

    def install_all(
        self, context: InstallContext, exclude: list[str] | None = None
    ) -> dict[str, PluginResult]:
        """Install all plugins in dependency order.

        Tracks installed files and plugins for potential rollback.
        Stops on first failure and logs error details for debugging.

        Args:
            context: InstallContext with shared installation utilities
            exclude: Optional list of plugin names to skip during installation

        Returns:
            Dictionary mapping plugin names to their installation results
        """
        results = {}
        order = self.get_execution_order()
        exclude_set = set(exclude) if exclude else set()

        # Reset tracking for this installation session
        self._installed_files = []
        self._installed_plugins = []

        for plugin_name in order:
            # Skip excluded plugins
            if plugin_name in exclude_set:
                continue

            plugin = self.plugins[plugin_name]
            result = plugin.install(context)
            results[plugin_name] = result

            if result.success:
                # Track successful installation for potential rollback
                self._installed_plugins.append(plugin_name)
                if result.installed_files:
                    self._installed_files.extend(result.installed_files)
            else:
                # Log error details for debugging
                context.logger.error(f"  ❌ Plugin failed: {result.message}")
                if result.errors:
                    for error in result.errors:
                        context.logger.error(f"    ❌ {error}")
                break

        return results

    def rollback_installation(self, context: InstallContext) -> None:
        """Rollback installation by removing installed files and restoring backup.

        This method should be called when plugin installation fails to restore
        the system to its pre-installation state.

        Rollback procedure:
        1. Remove files installed during this session
        2. Remove directories created by installed plugins
        3. Restore from backup if BackupManager is available
        4. Log rollback actions for debugging

        Args:
            context: InstallContext with shared installation utilities
        """
        context.logger.info("  ♻️ Rolling back installation...")

        # Remove tracked installed files
        removed_count = 0
        for file_path in self._installed_files:
            # Handle both string and Path objects
            path = Path(file_path) if isinstance(file_path, str) else file_path
            if path.exists():
                try:
                    path.unlink()
                    removed_count += 1
                except OSError as e:
                    context.logger.warn(f"  ⚠️ Could not remove {path}: {e}")

        if removed_count > 0:
            context.logger.info(f"  ✅ Removed {removed_count} installed files")

        # Clean up empty directories created by plugins
        for plugin_name in reversed(self._installed_plugins):
            plugin_dir = context.claude_dir / plugin_name
            if plugin_dir.exists() and plugin_dir.is_dir():
                try:
                    # Only remove if directory is empty or was created by this plugin
                    if not any(plugin_dir.iterdir()):
                        plugin_dir.rmdir()
                        context.logger.info(
                            f"    ✅ Removed empty directory: {plugin_dir}"
                        )
                except OSError:
                    pass  # Directory not empty or cannot be removed

        # Restore from backup if BackupManager is available
        if context.backup_manager is not None:
            context.logger.info("  ⏳ Restoring from backup...")
            backup_dir = context.backup_manager.backup_dir
            if backup_dir and backup_dir.exists():
                self._restore_from_backup(context, backup_dir)

        # Clear tracking
        self._installed_files = []
        self._installed_plugins = []

        context.logger.info("  🍾 Rollback complete")

    def _restore_from_backup(self, context: InstallContext, backup_dir: Path) -> None:
        """Restore files from backup directory.

        Args:
            context: InstallContext with shared installation utilities
            backup_dir: Path to backup directory
        """
        # Restore agents directory if it exists in backup
        backup_agents = backup_dir / "agents"
        if backup_agents.exists():
            target_agents = context.claude_dir / "agents"
            if target_agents.exists():
                shutil.rmtree(target_agents)
            shutil.copytree(backup_agents, target_agents)
            context.logger.info("  ✅ Agents restored from backup")

        # Restore commands directory if it exists in backup
        backup_commands = backup_dir / "commands"
        if backup_commands.exists():
            target_commands = context.claude_dir / "commands"
            if target_commands.exists():
                shutil.rmtree(target_commands)
            shutil.copytree(backup_commands, target_commands)
            context.logger.info("  ✅ Commands restored from backup")

    def verify_all(self, context: InstallContext) -> dict[str, PluginResult]:
        """Verify all plugins in dependency order.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            Dictionary mapping plugin names to their verification results
        """
        results = {}
        order = self.get_execution_order()

        for plugin_name in order:
            plugin = self.plugins[plugin_name]
            result = plugin.verify(context)
            results[plugin_name] = result

        return results

    def get_dependents(self, plugin_name: str) -> list[str]:
        """Get list of plugins that depend on the specified plugin.

        Args:
            plugin_name: Name of plugin to find dependents for

        Returns:
            List of plugin names that depend on the specified plugin
        """
        dependents = []
        for name, plugin in self.plugins.items():
            if plugin_name in plugin.get_dependencies():
                dependents.append(name)
        return dependents

    def uninstall(self, context: InstallContext, plugin_name: str) -> PluginResult:
        """Uninstall a specific plugin.

        Checks for dependent plugins before uninstallation. If other plugins
        depend on the target plugin, uninstallation is blocked.

        Args:
            context: InstallContext with shared installation utilities
            plugin_name: Name of plugin to uninstall

        Returns:
            PluginResult indicating success or failure with details
        """
        # Check if plugin exists
        if plugin_name not in self.plugins:
            return PluginResult(
                success=False,
                plugin_name=plugin_name,
                message=f"Plugin '{plugin_name}' not found or not registered",
            )

        # Check for dependents
        dependents = self.get_dependents(plugin_name)
        if dependents:
            return PluginResult(
                success=False,
                plugin_name=plugin_name,
                message=f"Cannot uninstall '{plugin_name}': dependent plugins exist ({', '.join(dependents)})",
            )

        # Get plugin and call its uninstall method
        plugin = self.plugins[plugin_name]
        if hasattr(plugin, "uninstall"):
            result = plugin.uninstall(context)
            if result.success:
                # Remove from registry on successful uninstall
                del self.plugins[plugin_name]
            return result
        else:
            # Plugin doesn't have uninstall method - just remove from registry
            del self.plugins[plugin_name]
            return PluginResult(
                success=True,
                plugin_name=plugin_name,
                message=f"Plugin '{plugin_name}' uninstalled successfully",
            )
