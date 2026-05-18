"""nwave-ai CLI: thin wrapper around nWave install/uninstall scripts."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from nwave_ai.doctor.context import DoctorContext
from nwave_ai.doctor.formatter import render_human, render_json
from nwave_ai.doctor.runner import run_doctor
from scripts.install.attribution_utils import (
    install_attribution_hook,
    read_attribution_preference,
    read_global_config,
    remove_attribution_hook,
    write_attribution_preference,
    write_global_config,
)
from scripts.shared.install_paths import GLOBAL_CONFIG_FILENAME


# ---------------------------------------------------------------------------
# D6 + AC-3: install-time density prompt
# ---------------------------------------------------------------------------


DensityPromptOutcome = Literal[
    "prompted",  # interactive prompt fired, user picked
    "default_silent",  # CI / --yes -> silent lean default
    "upgrade_silent",  # existing config without documentation key
    "noop_already_configured",  # documentation.density already set
]


def _prompt_density_choice() -> str:
    """Ask Marco once, interactively, which density to use.

    Returns "lean" or "full". Default if user just presses enter is "lean".
    Wrapped in its own function so unit tests can mock the I/O without faking
    typer's prompt machinery.
    """
    import typer

    print("Documentation density: lean (experienced) / full (first feature)?")
    raw_answer: str = typer.prompt("Choice", default="lean")
    answer = raw_answer.strip().lower()
    if answer not in {"lean", "full"}:
        # Unknown reply -> default to lean rather than loop forever.
        # (DELIVER scope: keep simple; rich validation deferred.)
        return "lean"
    return answer


def handle_install_density_prompt(
    config_dir: Path,
    *,
    non_interactive: bool,
) -> DensityPromptOutcome:
    """Run the D6 first-install density branch.

    Pure orchestration: caller passes config_dir + interactivity flag, this
    function decides whether to (a) skip, (b) prompt, or (c) write a silent
    default, then persists the choice via the existing global-config helpers.

    Cascade:
      1. Config file exists with `documentation.density` set -> noop.
      2. Config file exists but no `documentation` key -> silent lean default
         (AC-3.e — upgrade path).
      3. No config file at all + non_interactive -> silent lean default
         (AC-3.d — CI / --yes).
      4. No config file at all + interactive -> prompt user (AC-3.a/b).

    Args:
        config_dir: ~/.nwave directory (created lazily by writers).
        non_interactive: True when `--yes` was passed or stdin is not a TTY.

    Returns:
        Outcome literal describing which branch fired (helps callers log).
    """
    config_path = config_dir / GLOBAL_CONFIG_FILENAME
    config_file_exists = config_path.exists()
    existing_config = read_global_config(config_dir) if config_file_exists else {}
    documentation_block = existing_config.get("documentation", {})

    # Case 1: density already set -> idempotent no-op.
    if documentation_block.get("density") is not None:
        return "noop_already_configured"

    # Case 2: config exists but no documentation block -> silent default.
    if config_file_exists:
        _write_density_choice(config_dir, choice="lean")
        return "upgrade_silent"

    # Case 3: fresh install + non-interactive -> silent default.
    if non_interactive:
        _write_density_choice(config_dir, choice="lean")
        return "default_silent"

    # Case 4: fresh install + interactive -> prompt.
    choice = _prompt_density_choice()
    _write_density_choice(config_dir, choice=choice)
    return "prompted"


def _write_density_choice(config_dir: Path, *, choice: str) -> None:
    """Persist the chosen density alongside `expansion_prompt: ask-intelligent`.

    Uses read-modify-write to preserve unrelated keys (e.g. attribution).
    Per Decision 4 (2026-04-28), the fresh-install expansion prompt default
    is `ask-intelligent` (scoped trigger-based menu) — only Tier-2 items
    that match a fired trigger are shown to the user. This replaces the
    older broad `ask` default that surfaced the entire 8-item catalog.
    """
    config = read_global_config(config_dir)
    documentation_block = config.get("documentation", {})
    documentation_block["density"] = choice
    documentation_block.setdefault("expansion_prompt", "ask-intelligent")
    config["documentation"] = documentation_block
    write_global_config(config_dir, config)


def _get_version() -> str:
    """Get version from package metadata (installed) or __init__.py (dev)."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nwave-ai")
    except PackageNotFoundError:
        pass

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

    cmd = [sys.executable, str(script_path), *args]
    result = subprocess.run(cmd, cwd=str(project_root))
    return result.returncode


def _get_config_dir() -> Path:
    """Return the nWave config directory (~/.nwave/)."""
    return Path.home() / ".nwave"


def _extract_target_flag(
    args: list[str],
) -> tuple[Path | None, list[str], str | None]:
    """Parse and consume `--target <path>` (or `--target=<path>`) from args.

    Returns (resolved_target_path | None, remaining_args, error_message | None).

    The target is resolved via `Path.expanduser().resolve()` so that `~/...`,
    relative paths, and symlinks all collapse to a single canonical form
    before being applied as `CLAUDE_CONFIG_DIR` for the subprocess.

    If the resolved target equals `realpath($HOME)`, returns an error so the
    caller can exit 2 without mutating any filesystem state (the single
    highest-impact misconfiguration guard).
    """
    remaining: list[str] = []
    target: str | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--target":
            if i + 1 >= len(args):
                return (None, args, "--target requires a path argument")
            target = args[i + 1]
            i += 2
            continue
        if arg.startswith("--target="):
            target = arg.split("=", 1)[1]
            i += 1
            continue
        remaining.append(arg)
        i += 1

    if target is None:
        return (None, remaining, None)

    resolved = Path(target).expanduser().resolve()
    if resolved == Path.home().resolve():
        return (
            None,
            remaining,
            "--target must point to a Claude config directory "
            "(e.g. ~/.claude-nwave or ./.claude), not your home directory",
        )
    return (resolved, remaining, None)


def _handle_install(args: list[str]) -> int:
    """Run the install pipeline with first-run density prompt (D6).

    The density prompt is run BEFORE the heavyweight install_nwave.py
    subprocess so a CI host (--yes) gets the silent default and a
    real Marco gets one prompt. The density prompt does not block the
    install on failure — at worst the CI default ("lean") is written.

    Flags handled here:
        --target <path>    install into <path> instead of ~/.claude/
                           (sets CLAUDE_CONFIG_DIR for the subprocess; see
                           ADR-001). $HOME is refused with exit 2.
        --yes              non-interactive (CI / silent default)
        --density-only     run ONLY the density prompt and exit (test driving
                           port for acceptance tests; never a user flag)

    All other args pass through to install_nwave.py.
    """
    target, args, error = _extract_target_flag(args)
    if error is not None:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 2
    if target is not None:
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)

    pass_through_args: list[str] = []
    non_interactive = False
    density_only = False

    for arg in args:
        if arg == "--yes":
            non_interactive = True
            # Don't forward --yes to install_nwave.py (it doesn't recognise it).
            continue
        if arg == "--density-only":
            density_only = True
            continue
        pass_through_args.append(arg)

    # Detect non-interactive mode from environment if not explicit.
    if not non_interactive and not sys.stdin.isatty():
        non_interactive = True

    config_dir = _get_config_dir()
    outcome = handle_install_density_prompt(
        config_dir=config_dir, non_interactive=non_interactive
    )

    if outcome == "upgrade_silent":
        config_path = config_dir / GLOBAL_CONFIG_FILENAME
        print(
            "Documentation density default 'lean' written to "
            f"{config_path} (existing configuration upgraded)."
        )

    if density_only:
        return 0

    return _run_script("install_nwave.py", pass_through_args)


def _handle_uninstall(args: list[str]) -> int:
    """Run the uninstall pipeline.

    Flags handled here:
        --target <path>    uninstall from <path> instead of ~/.claude/
                           (sets CLAUDE_CONFIG_DIR for the subprocess; see
                           ADR-001). $HOME is refused with exit 2.

    All other args pass through to uninstall_nwave.py.
    """
    target, remaining, error = _extract_target_flag(args)
    if error is not None:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 2
    if target is not None:
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)
    return _run_script("uninstall_nwave.py", remaining)


def _handle_attribution(args: list[str]) -> int:
    """Handle 'attribution on|off|status' subcommand."""
    if not args:
        print("Usage: nwave-ai attribution <on|off|status>", file=sys.stderr)
        return 1

    action = args[0].lower()
    config_dir = _get_config_dir()

    if action == "on":
        write_attribution_preference(config_dir, enabled=True)
        install_attribution_hook(config_dir)
        print("Attribution enabled. Your commits will include the nWave credit line.")
        return 0

    if action == "off":
        write_attribution_preference(config_dir, enabled=False)
        remove_attribution_hook(config_dir)
        print(
            "Attribution disabled. Your commits will not include the nWave credit line."
        )
        return 0

    if action == "status":
        preference = read_attribution_preference(config_dir)
        if preference is True:
            print("Attribution is currently on.")
        else:
            print("Attribution is currently off.")
        return 0

    print(f"Unknown attribution action: {action}", file=sys.stderr)
    print("Usage: nwave-ai attribution <on|off|status>", file=sys.stderr)
    return 1


def _handle_doctor(args: list[str]) -> int:
    """Handle 'doctor [--json] [--fix] [--help]' subcommand."""
    json_output = False
    fix = False

    for arg in args:
        if arg in ("--help", "-h"):
            print("Usage: nwave-ai doctor [--json] [--fix]")
            print()
            print("Run diagnostic checks on the nWave installation.")
            print()
            print("Options:")
            print("  --json    Emit JSON output instead of human-readable text.")
            print("  --fix     Attempt to fix detected issues (not yet implemented).")
            print("  --help    Show this message and exit.")
            return 0
        elif arg == "--json":
            json_output = True
        elif arg == "--fix":
            fix = True
        else:
            print(f"Unknown option for doctor: {arg}", file=sys.stderr)
            print("Run 'nwave-ai doctor --help' for usage.", file=sys.stderr)
            return 2

    if fix:
        print(
            "--fix not yet implemented. "
            "Run `nwave-ai install` to restore a broken installation."
        )
        return 2

    context = DoctorContext.from_defaults()
    results = run_doctor(context)

    if json_output:
        print(render_json(results))
    else:
        print(render_human(results))

    if any(not r.passed for r in results):
        return 1
    return 0


def _handle_sync(args: list[str]) -> int:
    """Handle the `nwave-ai sync` subcommand (DDD-4).

    Mirrors each feature worktree's `docs/feature/<id>/feature-delta.md` to
    `<master>/.nwave/in-flight/<id>.md`, removing stale entries. On-demand
    only — no post-commit hook (vendor-neutrality rule).
    """
    for arg in args:
        if arg in ("--help", "-h"):
            print("Usage: nwave-ai sync")
            print()
            print(
                "Mirror in-flight feature-delta.md files from feature/* "
                "worktrees into <master>/.nwave/in-flight/."
            )
            print()
            print("Run from any path inside the master worktree.")
            return 0
        print(f"Unknown option for sync: {arg}", file=sys.stderr)
        print("Run 'nwave-ai sync --help' for usage.", file=sys.stderr)
        return 2

    from nwave_ai.sync import main as sync_main

    return sync_main()


def _handle_extract_gherkin(args: list[str]) -> int:
    """Handle 'extract-gherkin <path>' subcommand (US-06)."""
    from nwave_ai.feature_delta.cli import extract_gherkin_command

    if not args or args[0] in ("--help", "-h"):
        print("Usage: nwave-ai extract-gherkin <path>")
        print()
        print("Extract embedded Gherkin blocks from a feature-delta.md file.")
        print()
        print("Output begins with 'Feature: <feature-id>' followed by all")
        print("```gherkin ... ``` blocks concatenated in document order.")
        print()
        print("Exit codes:")
        print("  0   Extraction successful — output written to stdout")
        print("  1   No gherkin blocks found in the file")
        print("  65  Input error (file not found, unreadable)")
        return 0

    return extract_gherkin_command(args[0])


def _handle_migrate_feature(args: list[str]) -> int:
    """Handle 'migrate-feature <directory>' subcommand (US-08)."""
    from nwave_ai.feature_delta.cli import migrate_feature_command

    if not args or args[0] in ("--help", "-h"):
        print("Usage: nwave-ai migrate-feature <directory>")
        print()
        print("Migrate .feature files to embedded gherkin blocks in feature-delta.md.")
        print()
        print("Each .feature file is embedded as a fenced ```gherkin block.")
        print("A byte-identical round-trip check is performed before any file")
        print(
            "is modified. On success, originals are renamed to .feature.pre-migration."
        )
        print()
        print("Re-running on an already-migrated directory is a no-op (exit 0).")
        print()
        print("Exit codes:")
        print("  0   Migration succeeded (or already migrated — no-op)")
        print("  1   Round-trip check failed or input error")
        return 0

    return migrate_feature_command(args[0])


def _handle_validate_feature_delta(args: list[str]) -> int:
    """Handle 'validate-feature-delta <path> [--warn-only|--enforce] [--maturity-manifest <path>]'."""
    from nwave_ai.feature_delta.cli import validate_feature_delta_command

    if not args or args[0] in ("--help", "-h"):
        print("Usage: nwave-ai validate-feature-delta <path> [--warn-only | --enforce]")
        print()
        print("Validate a feature-delta.md file for cross-wave drift.")
        print()
        print("Options:")
        print("  --warn-only            (default) Exit 0 even when violations found.")
        print("                         Violations are reported with [WARN] prefix.")
        print("                         Switch criterion: 30 days post-ship OR >=3")
        print("                         features migrated voluntarily (see CHANGELOG).")
        print(
            "  --enforce              Exit 1 when violations found. Refused (exit 78)"
        )
        print("                         when maturity manifest marks any rule pending.")
        print(
            "  --maturity-manifest    Path to rule maturity manifest (overrides default)."
        )
        print()
        print("Exit codes:")
        print("  0   No violations (or warn-only mode — violations non-blocking)")
        print("  1   Violations found (enforce mode only)")
        print("  65  Input error (file not found, empty, unreadable)")
        print("  78  Misconfiguration (--enforce with pending rules in manifest)")
        return 0

    # Parse path + flags from args list.
    mode = "warn-only"
    fmt = "human"
    maturity_manifest_path: Path | None = None
    extra_rules: set[str] = set()
    cleaned: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--warn-only":
            mode = "warn-only"
        elif token == "--enforce":
            mode = "enforce"
        elif token.startswith("--format="):
            fmt = token[len("--format=") :]
        elif token == "--format" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 1
        elif token == "--maturity-manifest" and i + 1 < len(args):
            maturity_manifest_path = Path(args[i + 1])
            i += 1
        elif token == "--rule" and i + 1 < len(args):
            extra_rules.add(args[i + 1].upper())
            i += 1
        elif token.startswith("--rule="):
            extra_rules.add(token[len("--rule=") :].upper())
        else:
            cleaned.append(token)
        i += 1

    if not cleaned:
        print(
            "Usage: nwave-ai validate-feature-delta <path> [--warn-only | --enforce] [--format=json]",
            file=sys.stderr,
        )
        return 2

    enabled_rules = frozenset(extra_rules) if extra_rules else None
    return validate_feature_delta_command(
        cleaned[0],
        mode=mode,
        fmt=fmt,
        maturity_manifest_path=maturity_manifest_path,
        enabled_rules=enabled_rules,
    )


# ---------------------------------------------------------------------------
# Tool plugin install/uninstall (e.g. `nwave-ai plugin install dedup`)
# ---------------------------------------------------------------------------

# Registry of known nWave tool plugins.
# Key = short name shown to the user; value = PyPI package name.
# Hardcoded by design (Earned Trust: explicit > unverified discovery API).
# Add a new plugin by extending this dict and shipping a release.
KNOWN_PLUGINS: dict[str, str] = {
    "dedup": "nwave-dedup",
}


def _resolve_installer() -> tuple[list[str], str] | None:
    """Pick `pipx` if available (recommended for CLIs), else `pip`."""
    import shutil

    if shutil.which("pipx"):
        return (["pipx"], "pipx")
    if shutil.which("pip"):
        return (["pip"], "pip")
    return None


def _handle_plugin(args: list[str]) -> int:
    """Subcommand: install/uninstall/list nWave tool plugins."""
    if not args or args[0] in ("--help", "-h", "help"):
        print("Usage: nwave-ai plugin <subcommand> [args]")
        print()
        print("Subcommands:")
        print("  list                   List known plugins")
        print("  install <name>         Install a plugin (e.g. `dedup`)")
        print("  uninstall <name>       Remove an installed plugin")
        print()
        print("Known plugins:")
        for name, pkg in sorted(KNOWN_PLUGINS.items()):
            print(f"  {name:12s}  → {pkg}  (https://pypi.org/project/{pkg}/)")
        return 0

    sub = args[0]

    if sub == "list":
        for name, pkg in sorted(KNOWN_PLUGINS.items()):
            print(f"{name}\t{pkg}")
        return 0

    if sub not in ("install", "uninstall"):
        print(f"Unknown plugin subcommand: {sub}", file=sys.stderr)
        print("Run 'nwave-ai plugin --help' for usage.", file=sys.stderr)
        return 1

    if len(args) < 2:
        print(
            f"Missing plugin name. Usage: nwave-ai plugin {sub} <name>", file=sys.stderr
        )
        return 1

    name = args[1]
    if name not in KNOWN_PLUGINS:
        print(f"Unknown plugin: {name!r}", file=sys.stderr)
        print(f"Known plugins: {', '.join(sorted(KNOWN_PLUGINS))}", file=sys.stderr)
        return 1

    pkg = KNOWN_PLUGINS[name]
    installer = _resolve_installer()
    if installer is None:
        print(
            "Neither pipx nor pip is available on PATH. Install one of them and retry.",
            file=sys.stderr,
        )
        return 1
    cmd_prefix, tool = installer

    action = "install" if sub == "install" else "uninstall"
    print(f"Running: {tool} {action} {pkg}")
    try:
        result = subprocess.run([*cmd_prefix, action, pkg], check=False)
    except FileNotFoundError as exc:
        print(f"Failed to invoke {tool}: {exc}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(
            f"{tool} {action} failed (exit {result.returncode}). "
            f"See {tool}'s output above for details.",
            file=sys.stderr,
        )
        return result.returncode

    if sub == "install":
        # Earned Trust: verify the CLI actually became invokable.
        import shutil

        cli_name = pkg  # plugin CLI name == PyPI package name by convention
        if shutil.which(cli_name) is None:
            print(
                f"Warning: {tool} reported success but '{cli_name}' is not on "
                f"PATH yet. If you used pipx, you may need to restart your "
                f"shell or run 'pipx ensurepath'.",
                file=sys.stderr,
            )
            return 0
        print(f"OK: {cli_name} installed and on PATH.")
    else:
        print(f"OK: {pkg} uninstalled.")
    return 0


def _print_usage() -> int:
    ver = _get_version()
    print(f"nwave-ai {ver}")
    print()
    print("Usage: nwave-ai <command> [options]")
    print()
    print("Commands:")
    print("  install        Install nWave framework to ~/.claude/")
    print("  uninstall      Remove nWave framework from ~/.claude/")
    print("  doctor         Run diagnostics on the nWave installation")
    print(
        "  sync           Mirror in-flight feature-delta files to "
        "<master>/.nwave/in-flight/"
    )
    print("  attribution    Toggle commit attribution (on/off/status)")
    print("  outcomes       Register / check shipped outcomes (Tier-1 collision)")
    print("  plugin         Manage tool plugins (install/uninstall/list)")
    print("  version        Show nwave-ai version")
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

    if sys.argv[1] in ("--version", "-V"):
        print(f"nwave-ai {_get_version()}")
        return 0

    command = sys.argv[1]

    if command == "install":
        return _handle_install(sys.argv[2:])
    elif command == "uninstall":
        return _handle_uninstall(sys.argv[2:])
    elif command == "attribution":
        return _handle_attribution(sys.argv[2:])
    elif command == "doctor":
        return _handle_doctor(sys.argv[2:])
    elif command == "sync":
        return _handle_sync(sys.argv[2:])
    elif command == "validate-feature-delta":
        return _handle_validate_feature_delta(sys.argv[2:])
    elif command == "extract-gherkin":
        return _handle_extract_gherkin(sys.argv[2:])
    elif command == "migrate-feature":
        return _handle_migrate_feature(sys.argv[2:])
    elif command == "outcomes":
        from nwave_ai.outcomes.cli import handle_outcomes

        return handle_outcomes(sys.argv[2:])
    elif command == "plugin":
        return _handle_plugin(sys.argv[2:])
    elif command == "version":
        print(f"nwave-ai {_get_version()}")
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'nwave-ai --help' for usage.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
