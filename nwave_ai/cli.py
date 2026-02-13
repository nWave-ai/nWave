"""nwave-ai CLI: thin wrapper around nWave install/uninstall scripts."""

import subprocess
import sys
from pathlib import Path


def _get_version() -> str:
    """Get version from package metadata (installed) or __init__.py (dev)."""
    from importlib.metadata import PackageNotFoundError, version

    for pkg_name in ("nwave-ai", "nwave"):
        try:
            return version(pkg_name)
        except PackageNotFoundError:
            continue

    from nwave_ai import __version__

    return __version__


def _get_project_root() -> Path:
    """Find the project root (where scripts/install/ lives)."""
    return Path(__file__).parent.parent


def _run_script(script_name: str, args: list[str]) -> int:
    """Run an install script as a subprocess."""
    project_root = _get_project_root()
    script_path = project_root / "scripts" / "install" / script_name

    if not script_path.exists():
        print(f"Error: {script_name} not found at {script_path}", file=sys.stderr)
        print("The nwave-ai package may not be installed correctly.", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script_path)] + args
    result = subprocess.run(cmd, cwd=str(project_root))
    return result.returncode


def _print_usage() -> int:
    ver = _get_version()
    print(f"nwave-ai {ver}")
    print()
    print("Usage: nwave-ai <command> [options]")
    print()
    print("Commands:")
    print("  install     Install nWave framework to ~/.claude/")
    print("  uninstall   Remove nWave framework from ~/.claude/")
    print("  version     Show nwave-ai version")
    print()
    print("Install options:")
    print("  --dry-run       Preview without making changes")
    print("  --backup-only   Create backup only")
    print("  --restore       Restore from backup")
    print()
    print("Example:")
    print("  nwave-ai install")
    return 0


def main() -> int:
    """CLI entry point for nwave-ai."""
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        return _print_usage()

    command = sys.argv[1]

    if command == "install":
        return _run_script("install_nwave.py", sys.argv[2:])
    elif command == "uninstall":
        return _run_script("uninstall_nwave.py", sys.argv[2:])
    elif command == "version":
        print(f"nwave-ai {_get_version()}")
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'nwave-ai --help' for usage.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
