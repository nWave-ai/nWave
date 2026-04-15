"""Centralized installation path constants -- single source of truth.

Replaces 10+ scattered hardcoded path constructions across installer
plugins, verifier, and build scripts.

All consumers should import from this module::

    from scripts.shared.install_paths import AGENTS_SUBDIR, agents_dir
"""

from __future__ import annotations

import sys
from pathlib import Path, PureWindowsPath


# Relative path segments (appended to claude_dir by callers)
AGENTS_SUBDIR = Path("agents") / "nw"
SKILLS_SUBDIR = Path("skills")
TEMPLATES_SUBDIR = Path("templates")
DES_LIB_SUBDIR = Path("lib") / "python" / "des"
SCRIPTS_SUBDIR = Path("scripts")
COMMANDS_LEGACY_SUBDIR = Path("commands") / "nw"  # deprecated, cleanup only
MANIFEST_FILENAME = "nwave-manifest.txt"


def agents_dir(claude_dir: Path) -> Path:
    """Return the agents installation directory."""
    return claude_dir / AGENTS_SUBDIR


def skills_dir(claude_dir: Path) -> Path:
    """Return the skills installation directory."""
    return claude_dir / SKILLS_SUBDIR


def templates_dir(claude_dir: Path) -> Path:
    """Return the templates installation directory."""
    return claude_dir / TEMPLATES_SUBDIR


def des_dir(claude_dir: Path) -> Path:
    """Return the DES library installation directory."""
    return claude_dir / DES_LIB_SUBDIR


def manifest_path(claude_dir: Path) -> Path:
    """Return the installation manifest file path."""
    return claude_dir / MANIFEST_FILENAME


# -- Python command resolution ------------------------------------------------

# Literal pattern used in source templates for portable Python resolution.
# Installed files replace this with the resolved concrete path.
PYTHON_CMD_SUBSTITUTION = "$(command -v python3 || command -v python)"


def resolve_python_command() -> str:
    """Return the base Python command name for skill/command templates.

    Returns 'python3' unconditionally. Templates that consume this value
    are rendered into markdown documents that run in contexts with PATH
    resolution, so the base command name is what callers want -- never
    an absolute path.

    For contexts that need an absolute path (non-shell spawn), see
    resolve_python_command_for_spawn(). For $HOME-prefixed paths in
    shell-execution contexts (settings.json hook commands), see
    DESPlugin._resolve_python_path().
    """
    return "python3"


def resolve_python_command_for_spawn() -> str:
    """Return an absolute forward-slash path to the current Python interpreter.

    Use when the consuming code spawns the interpreter without a shell:
    TypeScript Bun.spawn, Node child_process.spawn, Python subprocess.run
    without shell=True, posix_spawn/CreateProcess directly.

    Cross-platform safety: uses Path.as_posix() so the result contains no
    backslashes on any platform. This lets the path embed safely into a
    TypeScript double-quoted string literal without triggering escape-
    sequence interpretation (e.g. \\U unicode escape, \\n newline).
    Windows APIs accept forward-slash paths since Windows 2000.

    The .venv fallback is preserved: when the installer runs from a
    project-local virtual environment (development, CI), returns 'python3'
    to avoid leaking development paths into user-installed artifacts.

    For shell-execution contexts (settings.json hook commands, bash
    scripts where $HOME is expanded), use the existing $HOME-based
    pattern in DESPlugin._resolve_python_path() instead.
    For markdown templates consumed by various runtimes, use
    resolve_python_command() (basename-only) instead.
    """
    python_path = sys.executable
    if "/.venv/" in python_path or "\\.venv\\" in python_path:
        return "python3"
    return (
        PureWindowsPath(python_path).as_posix()
        if "\\" in python_path
        else Path(python_path).as_posix()
    )


def resolve_des_lib_path_for_spawn() -> str:
    """Return an absolute forward-slash path to the DES library directory.

    Same rationale as resolve_python_command_for_spawn: consumers pass
    this to non-shell contexts (Bun.spawn env vars setting PYTHONPATH,
    Python subprocess.run without shell=True) where shell variable
    expansion does NOT happen, so '$HOME' stays literal and must be
    resolved at install time.
    """
    return (Path.home() / ".claude" / "lib" / "python").as_posix()
