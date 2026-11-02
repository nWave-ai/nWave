"""nwave-ai CLI: thin wrapper around nWave install/uninstall scripts."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


_DISTRIBUTION_ROOT = str(Path(__file__).resolve().parent.parent)


def _prefer_current_distribution() -> None:
    """Keep this wheel/checkout ahead of legacy namespace-package fallbacks."""
    if _DISTRIBUTION_ROOT in sys.path:
        sys.path.remove(_DISTRIBUTION_ROOT)
    sys.path.insert(0, _DISTRIBUTION_ROOT)


# Do this before importing installer modules: an old ~/.claude runtime can
# otherwise supply a stale namespace-package ``scripts`` implementation.
_prefer_current_distribution()

import nwave_ai  # noqa: E402
from nwave_ai.doctor.checks.framework_files import FrameworkFilesCheck  # noqa: E402
from nwave_ai.doctor.checks.hook_python_path import HookPythonPathCheck  # noqa: E402
from nwave_ai.doctor.checks.hooks_registered import HooksRegisteredCheck  # noqa: E402
from nwave_ai.doctor.context import DoctorContext  # noqa: E402
from nwave_ai.doctor.formatter import render_human, render_json  # noqa: E402
from nwave_ai.doctor.runner import run_doctor  # noqa: E402
from nwave_ai.platform.locations import NWaveLocations  # noqa: E402
from nwave_ai.platform.result import Failure  # noqa: E402
from scripts.install.attribution_utils import (  # noqa: E402
    cleanup_legacy_attribution_hook,
    migrate_legacy_hook,
    migrate_legacy_settings_attribution,
    read_global_config,
    write_attribution_preference,
)
from scripts.shared.install_paths import nwave_config_dir  # noqa: E402
from scripts.shared.version import VersionResolutionError  # noqa: E402


def _refuse_version_resolution(exc: VersionResolutionError) -> int:
    """Print the WHAT/WHY/HOW refusal for a failed version resolution."""
    print(str(exc), file=sys.stderr)
    return 1


def _handle_update(
    args: list[str], *, wrapper_registration=None, replacement_lease=None
) -> int:
    """Observe releases or apply an owner-bound update with explicit consent."""
    if args[:2] == ["consent", "controlled-launch"]:
        return _handle_controlled_launch_consent(args[2:])
    if args[:1] == ["sessions"]:
        return _handle_update_sessions(args[1:])
    if len(args) in (3, 4) and args[0] == "consent":
        permission, choice = args[1:3]
        confirmation = args[3:]
        if (
            permission not in ("check", "install")
            or choice not in ("on", "off")
            or confirmation not in ([], [_CONFIRM_OLD_SESSIONS_CLOSED])
            or (confirmation and (permission, choice) != ("install", "on"))
        ):
            print(
                "Usage: nwave-ai update consent <check|install> <on|off> "
                f"(install on: {_CONFIRM_OLD_SESSIONS_CLOSED} the first time)",
                file=sys.stderr,
            )
            return 1
        try:
            config_dir = _require_mutating_config_dir()
        except ValueError as error:
            return _refuse_mutating_location(error)
        from nwave_ai.platform.config_writer import ConfigWriter

        if (permission, choice) == ("install", "on"):
            refused = _record_old_sessions_closed(
                config_dir.parent, confirmed=bool(confirmation)
            )
            if refused:
                return refused

        def set_permission(document: dict) -> None:
            previous = document.get("updates")
            updates = dict(previous) if isinstance(previous, dict) else {}
            updates["check"] = updates.get("check") is True
            updates["install"] = updates.get("install") is True
            updates[permission] = choice == "on"
            document["updates"] = updates

        try:
            ConfigWriter(
                home_dir=config_dir.parent, repo_root=Path.cwd()
            ).update_global(set_permission)
        except Exception as error:
            print(
                f"WHAT: update consent was not written. WHY: {error}. "
                "HOW: repair the selected global config and retry the consent command.",
                file=sys.stderr,
            )
            return 1
        print(f"Automatic update {permission}: {choice}.")
        if (permission, choice) == ("install", "on"):
            from nwave_ai.platform.session_registry import ATTESTATION_RISK

            print(f"Residual risk: {ATTESTATION_RISK}.")
        return 0

    is_check = args == ["--check"]
    is_apply = len(args) == 3 and args[:2] == ["--yes", "--root"]
    is_recovery = args == ["--recover", "--yes", "--confirm-stopped"]
    if not is_check and not is_apply and not is_recovery:
        print(
            "Usage: nwave-ai update --check | --yes --root PATH | "
            "--recover --yes --confirm-stopped | "
            "consent <check|install> <on|off> | sessions [close KEY --confirm-closed]",
            file=sys.stderr,
        )
        return 1

    from nwave_ai.update.service import UpdateService

    if is_recovery:
        print(
            "Recovery acknowledgement: all previous updater/installer descendants "
            "have stopped and affected host sessions are closed.",
            flush=True,
        )
        outcome = UpdateService().recover(
            on_stage=lambda stage, state: print(f"{stage}: {state}", flush=True),
        )
        return _report_update_outcome(outcome)
    pending = UpdateService.pending_update()
    if pending is not None:
        return _report_update_outcome(pending)

    try:
        # This is the only current-version read: product identity remains owned
        # by nwave_ai's existing lazy projection.
        current_version = nwave_ai.__version__
    except VersionResolutionError as exc:
        return _refuse_version_resolution(exc)

    from packaging.version import InvalidVersion, Version

    from nwave_ai.update import ReleaseDiscoveryRefusal, discover_latest_stable_release

    try:
        parsed_current_version = Version(current_version)
        if (
            parsed_current_version.is_prerelease
            or parsed_current_version.is_devrelease
            or parsed_current_version.local
        ):
            print(
                "WHAT: the selected beta or dev release has no supported stable update path. "
                "WHY: a PyPI stable release is a different channel and could remove "
                "the selected assets. HOW: use the selected source or release channel's "
                "explicit install instructions.",
                file=sys.stderr,
            )
            return 1
        if is_check:
            install = read_global_config(_get_config_dir()).get("install")
            if isinstance(install, dict) and install.get("dev_mode") is True:
                print(
                    "WHAT: the selected --dev install has no supported stable update check. "
                    "WHY: PyPI stable release availability does not establish compatible "
                    "private dev assets. HOW: inspect the source checkout's release "
                    "route and reinstall with --dev for the selected host.",
                    file=sys.stderr,
                )
                return 1
        origin = UpdateService.release_origin()
        if origin is not None:
            print(
                f"WHAT: update stopped at {origin.failed_stage}. WHY: {origin.cause}. "
                f"Command: `no process`. HOW: {origin.recovery}.",
                file=sys.stderr,
            )
            return 1
        latest_version = discover_latest_stable_release()
    except ReleaseDiscoveryRefusal as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except InvalidVersion as exc:
        print(
            "WHAT: the installed nwave-ai version cannot be compared to a public release. "
            f"WHY: {exc}. "
            "HOW: reinstall nwave-ai with valid PEP 440 version metadata.",
            file=sys.stderr,
        )
        return 1

    if is_check:
        state = (
            "update-available"
            if latest_version > parsed_current_version
            else "up-to-date"
        )
        print(f"Installed version: {current_version}")
        print(f"Latest stable release: {latest_version}")
        print(f"Status: {state}")
        return 0

    from nwave_ai.update.activity import ReplacementLease

    # The exclusive update lock is taken only after every read-only preflight
    # and held until the last stage ends, so session registration waits for
    # the whole replacement and a refused preflight writes nothing.
    lease = replacement_lease or ReplacementLease(wrapper_registration)
    try:
        outcome = UpdateService().apply(
            current_version=parsed_current_version,
            discovered_version=latest_version,
            root=Path(args[2]),
            on_stage=lambda stage, state: print(f"{stage}: {state}", flush=True),
            before_replacement=lease.before_replacement,
        )
    finally:
        lease.close()
    return _report_update_outcome(outcome)


def _report_update_outcome(outcome) -> int:
    if outcome.state == "up-to-date":
        print(f"nwave-ai is up-to-date ({outcome.version}).")
        return 0
    if outcome.state == "refused":
        stage = outcome.failed_stage or "package-owner"
        command = " ".join(outcome.command) if outcome.command else "no process"
        recovery = (
            outcome.recovery or "verify the running package owner and retry explicitly"
        )
        print(
            f"WHAT: update stopped at {stage}. WHY: {outcome.cause}. "
            f"Command: `{command}`. HOW: {recovery}.",
            file=sys.stderr,
        )
        return 1

    # ``succeeded`` is the only state that carries a completed target version.
    print(f"Updated nwave-ai to {outcome.version}.")
    return 0


_CONFIRM_OLD_SESSIONS_CLOSED = "--confirm-old-sessions-closed"


def _record_old_sessions_closed(agents_home: Path, *, confirmed: bool) -> int:
    """Require, then record, the one-time closure attestation for old sessions.

    Returns 0 when the acknowledgement is recorded (now or before), else the
    exit code of a refusal that wrote nothing.
    """
    from nwave_ai.platform.session_registry import (
        ATTESTATION_RISK,
        SessionActivityRegistry,
    )

    registry = SessionActivityRegistry(agents_home)
    if not registry.legacy_acknowledgement_problem():
        return 0
    if not confirmed:
        print(
            "WHAT: automatic installation consent was not written. "
            "WHY: sessions that started before the global activity registry are not "
            "recorded, so an update could replace the installation during their wave; "
            f"{ATTESTATION_RISK}. "
            "HOW: close every host session that uses this installation, "
            f"then run `nwave-ai update consent install on {_CONFIRM_OLD_SESSIONS_CLOSED}`.",
            file=sys.stderr,
        )
        return 1
    try:
        with registry.exclusive(10.0) as acquired:
            if not acquired:
                print(
                    "WHAT: automatic installation consent was not written. WHY: an update "
                    f"holds {registry.lock_file}. HOW: wait for it to finish, then retry.",
                    file=sys.stderr,
                )
                return 1
            registry.acknowledge_legacy_sessions_closed()
    except OSError as exc:
        print(
            f"WHAT: automatic installation consent was not written. WHY: {exc}. "
            "HOW: repair the selected agents home's .nwave/activity directory and retry.",
            file=sys.stderr,
        )
        return 1
    return 0


def _handle_controlled_launch_consent(args: list[str]) -> int:
    if args not in (["on", "--confirm-controlled-launch"], ["off"]):
        print(
            "Usage: nwave-ai update consent controlled-launch on --confirm-controlled-launch | off",
            file=sys.stderr,
        )
        return 1
    try:
        config_dir = _require_mutating_config_dir()
        from nwave_ai.platform.config_writer import ConfigWriter

        def set_commitment(document: dict) -> None:
            previous = document.get("updates")
            updates = dict(previous) if isinstance(previous, dict) else {}
            updates["controlled_launch"] = args[0] == "on"
            document["updates"] = updates

        ConfigWriter(home_dir=config_dir.parent, repo_root=Path.cwd()).update_global(
            set_commitment
        )
    except Exception as exc:
        print(f"Controlled-launch commitment was not written: {exc}", file=sys.stderr)
        return 1
    print(f"Controlled-launch commitment: {args[0]}.")
    if args[0] == "on":
        print(
            "You confirm that future sessions sharing this package use `nwave-ai run HOST -- ARGS`. Direct launches, disabled hooks and detached work are not covered: close that work before allowing automatic replacement."
        )
    return 0


def _handle_run(args: list[str]) -> int:
    if len(args) < 2 or args[1] != "--":
        print(
            "Usage: nwave-ai run <claude-code|codex|opencode|copilot> -- [HOST_ARGS ...]",
            file=sys.stderr,
        )
        return 1
    from nwave_ai.update.managed import run_host

    return run_host(args[0], args[2:], update=_handle_update)


def _handle_update_sessions(args: list[str]) -> int:
    """List registered host sessions, or close one the operator attests ended."""
    from nwave_ai.platform.session_registry import SessionActivityRegistry

    registry = SessionActivityRegistry.selected()
    if registry is None:
        print(
            "WHAT: the activity registry was not read. WHY: the selected agents home is "
            "invalid. HOW: set NWAVE_AGENTS_HOME to an absolute path or unset it, then retry.",
            file=sys.stderr,
        )
        return 1
    from nwave_ai.update.package_activity import PackageActivityLease

    package = PackageActivityLease.for_interpreter()
    registries = [registry] + ([package.registry] if package is not None else [])
    if not args:
        try:
            records = tuple(
                record for current in registries for record in current.sessions()
            )
        except OSError as exc:
            print(
                f"WHAT: the activity registry was not read. WHY: {exc}. "
                f"HOW: repair {registry.root} and retry.",
                file=sys.stderr,
            )
            return 1
        problem = registry.legacy_acknowledgement_problem()
        print(f"Older-session confirmation: {problem if problem else 'recorded'}.")
        if not records:
            print("Registered sessions: none.")
        for record in {record.key: record for record in records}.values():
            if record.problem:
                print(f"{record.key}  UNKNOWN  {record.problem}")
            else:
                print(
                    f"{record.key}  {record.host}  {record.cwd}  since {record.registered_at}"
                )
        return 0
    if len(args) == 3 and args[0] == "close" and args[2] == "--confirm-closed":
        try:
            if package is not None and not package.acquire(exclusive=True):
                print(
                    "No record closed: a controlled host or updater still uses this package.",
                    file=sys.stderr,
                )
                return 1
            closed = False
            for current in registries:
                with current.exclusive(10.0) as acquired:
                    if not acquired:
                        print(
                            f"No record closed in {current.root}: its update lock is busy.",
                            file=sys.stderr,
                        )
                        return 1
                    closed = current.close_session(args[1]) or closed
        except OSError as exc:
            print(
                f"WHAT: no session record was closed. WHY: {exc}. "
                f"HOW: repair {registry.root} and retry.",
                file=sys.stderr,
            )
            return 1
        finally:
            if package is not None:
                package.close()
        if not closed:
            print(
                f"WHAT: no registered session is named {args[1]!r}. WHY: the key does not "
                "match a registry entry. HOW: run `nwave-ai update sessions` and copy the key.",
                file=sys.stderr,
            )
            return 1
        print(f"Closed session record {args[1]} on your confirmation that it ended.")
        return 0
    print(
        "Usage: nwave-ai update sessions [close KEY --confirm-closed]",
        file=sys.stderr,
    )
    return 1


def _get_project_root() -> Path:
    """Find the project root (where scripts/install/ lives)."""
    return Path(__file__).parent.parent


def _run_script(
    script_name: str, args: list[str], *, user_project_root: Path | None = None
) -> int:
    """Run an install script, carrying the caller project only to that process."""
    project_root = _get_project_root()
    script_path = project_root / "scripts" / "install" / script_name

    if not script_path.exists():
        print(f"Error: {script_name} not found at {script_path}", file=sys.stderr)
        print("The nwave-ai package may not be installed correctly.", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script_path), *args]
    environment = os.environ.copy()
    if user_project_root is not None:
        environment["NWAVE_PROJECT_ROOT"] = str(user_project_root.resolve())
    result = subprocess.run(cmd, cwd=str(project_root), env=environment)
    return result.returncode


def _get_config_dir() -> Path:
    """Return the read-compatible nWave config directory for this destination."""
    return nwave_config_dir()


def _require_mutating_config_dir() -> Path:
    """Resolve the selected global config directory or refuse before a write.

    ``nwave_config_dir`` retains its native-home fallback for legacy read-only
    callers. CLI commands that publish configuration must instead observe the
    same ``NWaveLocations`` failure returned to the installer, so a relative
    override never redirects a write to the operator's native home.
    """
    locations = NWaveLocations.resolve(
        home=Path.home(),
        repo_root=Path.cwd(),
        agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
        claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
        codex_config_override=os.environ.get("CODEX_HOME"),
    )
    if isinstance(locations, Failure):
        raise ValueError(locations.error)
    return locations.unwrap().agents_home / ".nwave"


def _refuse_mutating_location(error: ValueError) -> int:
    """Render one explicit selected-home refusal for a CLI write command."""
    print(
        "WHAT: configuration was not written. "
        f"WHY: {error}. "
        "HOW: set NWAVE_AGENTS_HOME, CLAUDE_CONFIG_DIR, and CODEX_HOME to "
        "absolute paths or unset them and retry.",
        file=sys.stderr,
    )
    return 1


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
    """Run the installer without prompting for inert documentation density.

    ``--yes`` bypasses interactive project guidance prompts; ``--platform``
    and other installer arguments pass through unchanged. ``--target`` selects
    a Claude Code profile, with ``$HOME`` refused as an unsafe target. An
    invalid active wave-end expansion preference refuses before installation.

    Flags handled here:
        --platform <tool>  target agentic tool to provision for
                           (claude-code / opencode / codex / cursor / copilot / omp /
                           devin, or auto / all). Forwarded
                           unchanged to install_nwave.py; this is the
                           entry point the cross-OS RC smoke matrix depends
                           on (ADR-PLAT-007).
        --target <path>    install into <path> instead of ~/.claude/
                           (sets CLAUDE_CONFIG_DIR for the subprocess; see
                           ADR-001). $HOME is refused with exit 2.
        --yes              non-interactive (CI / silent default)
        --density-only     run ONLY the density prompt and exit (test driving
                           port for acceptance tests; never a user flag)

    All other args (including --platform) pass through to install_nwave.py.
    """
    # The installer already owns this subcommand's public help text.  Dispatch
    # it before parsing targets or constructing any write-capable preflight so
    # discovery remains usable even when an actual installation is blocked.
    if "--help" in args or "-h" in args:
        return _run_script("install_nwave.py", ["--help"])

    # The updater synchronizes installed assets without reenrolling project
    # guidance that the project owner may have declined. A backup-only run
    # writes nothing outside the backup, so it never syncs guidance either.
    sync_project_guidance = (
        "--no-project-guidance" not in args and "--backup-only" not in args
    )
    args = [arg for arg in args if arg != "--no-project-guidance"]
    target, args, error = _extract_target_flag(args)
    if error is not None:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 2
    if target is not None:
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)

    pass_through_args = [arg for arg in args if arg != "--yes"]
    non_interactive = "--yes" in args or not sys.stdin.isatty()

    # A completed wave reads expansion_prompt, so reject an invalid explicit
    # choice before installing. Legacy density is not an install control.
    try:
        config_dir = _require_mutating_config_dir()
        documentation = read_global_config(config_dir).get("documentation")
        if isinstance(documentation, dict) and "expansion_prompt" in documentation:
            from nwave_ai.platform.documentation_density import resolve_density

            resolve_density(
                {
                    "documentation": {
                        "expansion_prompt": documentation["expansion_prompt"]
                    }
                }
            )
    except ValueError as error:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 1

    # Refuse unsafe Codex ownership before installation writes user state.
    from scripts.install.install_nwave import (
        NWaveInstaller,
        _resolve_platform_override,
    )

    platform = "auto"
    for index, arg in enumerate(pass_through_args):
        if arg.startswith("--platform="):
            platform = arg.split("=", 1)[1]
        elif arg == "--platform" and index + 1 < len(pass_through_args):
            platform = pass_through_args[index + 1]
    ownership_preflight = NWaveInstaller(
        dry_run=True, platform_override=_resolve_platform_override(platform)
    )
    if not ownership_preflight.validate_codex_ownership_preflight():
        return 1
    caller_project_root = Path.cwd().resolve()
    if "--dry-run" in pass_through_args:
        return _run_script(
            "install_nwave.py",
            pass_through_args,
            user_project_root=caller_project_root,
        )

    # The installer runs from its packaged source root so it can find its
    # assets. Preserve the caller's repository separately: configuration and
    # generated guidance belong to that user project, never the source tree.
    result = _run_script(
        "install_nwave.py",
        pass_through_args,
        user_project_root=caller_project_root,
    )
    if result != 0:
        return result

    # Project guidance belongs to the caller's project for every resolved host,
    # independently of which host-specific assets the installer provisions.
    if sync_project_guidance:
        try:
            _sync_project_claude_section(
                "enable", caller_project_root, assume_yes=non_interactive
            )
        except OSError as exc:
            print(f"  (could not sync guidance sections: {exc})", file=sys.stderr)

    return 0


def _handle_uninstall(args: list[str]) -> int:
    """Run the uninstall pipeline.

    Flags handled here:
        --target <path>    uninstall from <path> instead of ~/.claude/
                           (sets CLAUDE_CONFIG_DIR for the subprocess; see
                           ADR-001). $HOME is refused with exit 2. When set,
                           implies `--force` (scripted/test mode -- no
                           interactive prompts).

    All other args pass through to uninstall_nwave.py.
    """
    target, remaining, error = _extract_target_flag(args)
    if error is not None:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 2
    if target is not None:
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)
        # Scripted/test mode: skip interactive confirmation prompts. The
        # operator named an explicit target path -- they know what they're
        # uninstalling.
        if "--force" not in remaining:
            remaining = [*remaining, "--force"]
    try:
        caller_project_root = Path.cwd().resolve()
    except FileNotFoundError:
        print(
            "nwave-ai: the current directory no longer exists, so the project "
            "nWave was installed from cannot be located. Change to an existing "
            "directory and run uninstall again.",
            file=sys.stderr,
        )
        return 1
    return _run_script(
        "uninstall_nwave.py", remaining, user_project_root=caller_project_root
    )


def _handle_attribution(args: list[str]) -> int:
    """Handle 'attribution on|off|status' subcommand.

    Flags handled here:
        --target <path>    toggle attribution for <path> instead of
                           ~/.claude/ (sets CLAUDE_CONFIG_DIR for this
                           process; see ADR-001). Mirrors install/uninstall
                           (_handle_install / _handle_uninstall) so a
                           multi-profile setup toggles the profile actually
                           named, not always the default.
    """
    target, args, error = _extract_target_flag(args)
    if error is not None:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 2
    if target is not None:
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)

    if not args:
        print("Usage: nwave-ai attribution <on|off|status>", file=sys.stderr)
        return 1

    action = args[0].lower()
    # CLAUDE_CONFIG_DIR / --target scoped (same property install/uninstall
    # already resolve on), NOT a fixed ~/.claude -- so the hook is
    # registered/removed in the profile actually in scope, and the success
    # message can name it (never a silent "success" about the wrong path).
    from scripts.install.install_utils import PathUtils

    claude_dir = PathUtils.get_claude_config_dir()

    if action == "on":
        from scripts.install.host_attribution import HostAttributionPolicy

        try:
            config_dir = _require_mutating_config_dir()
        except ValueError as error:
            return _refuse_mutating_location(error)
        write_attribution_preference(config_dir, enabled=True)
        # ADR-CA-007: the activation-gated PreToolUse hook (universal pre-tool-use
        # adapter) is the SOLE attribution mechanism, observing attribution.enabled
        # at invocation time. Clean any legacy independent entry. Fail-open.
        try:
            cleanup_legacy_attribution_hook(claude_dir=claude_dir)
        except Exception:
            pass
        message = (
            "Attribution enabled. New Claude commits will carry the nWave "
            "credit via the universal handler (observes the preference at "
            "commit time)."
        )
        if target is not None:
            message += f" (target: {claude_dir})"
        print(message)
        policy = HostAttributionPolicy.from_install_record(config_dir)
        for mechanism in policy.mechanisms_in(Path.cwd()):
            print(mechanism.install(config_dir).report())
        return 0

    if action == "off":
        try:
            config_dir = _require_mutating_config_dir()
        except ValueError as error:
            return _refuse_mutating_location(error)
        write_attribution_preference(config_dir, enabled=False)
        # ADR-CA-007 DDD-3: clean any legacy nWave-managed settings credit,
        # preserving a user-modified value. Route through the claude_dir seam
        # explicitly so the sandbox injection holds (fail-open: never raises).
        migrate_legacy_settings_attribution(config_dir, claude_dir=claude_dir)
        # DDD-3: remove the stale independent attribution PreToolUse entry.
        # Contained so it never breaks the toggle.
        try:
            cleanup_legacy_attribution_hook(claude_dir=claude_dir)
        except Exception:
            pass
        # Root cause C: 'off' is the remediation affordance, so it must also
        # remove the orphaned legacy prepare-commit-msg git shim (hardened in
        # migrate_legacy_hook to scan every candidate hooks dir). Without this,
        # a machine already broken by an orphaned shim cannot recover with the
        # obvious command. Contained so it never breaks the toggle (fail-open).
        try:
            migrate_legacy_hook(config_dir=config_dir)
        except Exception:
            pass
        message = (
            "Attribution disabled. New Claude commits will not carry the nWave "
            "credit (the universal handler observes the preference at commit time)."
        )
        if target is not None:
            message += f" (target: {claude_dir})"
        print(message)
        return 0

    if action == "status":
        from nwave_ai.platform.activation import resolve_activation
        from nwave_ai.platform.config import NWaveConfig

        try:
            config = NWaveConfig(cwd=Path.cwd())
            effective, sources = config.effective_config_with_sources()
            active = resolve_activation(config.enabled_for_repo, config.activation_mode)
        except Exception:
            # A diagnostic cannot claim credit when the config cannot be read.
            print("Attribution is currently off.")
            print("Attribution is inactive for this repo.")
            return 0

        print(
            f"Attribution is currently {'on' if effective['attribution'] else 'off'}."
        )
        print(f"Preference source: {sources['attribution']}.")
        print(
            f"Attribution is {'active' if active and effective['attribution'] else 'inactive'} for this repo."
        )
        return 0

    print(f"Unknown attribution action: {action}", file=sys.stderr)
    print("Usage: nwave-ai attribution <on|off|status>", file=sys.stderr)
    return 1


class _SilentLogger:
    """Logger handed to plugin verifiers: the doctor prints its own report."""

    def info(self, _msg: str) -> None:
        pass

    def error(self, _msg: str) -> None:
        pass

    def warn(self, _msg: str) -> None:
        pass


def _verifying_plugins(host: str) -> list:
    """The installation plugins whose ``verify()`` speaks for a native host."""
    if host == "omp":
        from scripts.install.plugins.omp_agents_plugin import OmpAgentsPlugin
        from scripts.install.plugins.omp_commands_plugin import OmpCommandsPlugin
        from scripts.install.plugins.omp_skills_plugin import OmpSkillsPlugin

        return [OmpSkillsPlugin(), OmpAgentsPlugin(), OmpCommandsPlugin()]
    if host == "opencode":
        from scripts.install.plugins.opencode_agents_plugin import (
            OpenCodeAgentsPlugin,
        )
        from scripts.install.plugins.opencode_commands_plugin import (
            OpenCodeCommandsPlugin,
        )
        from scripts.install.plugins.opencode_skills_plugin import (
            OpenCodeSkillsPlugin,
        )

        return [
            OpenCodeSkillsPlugin(),
            OpenCodeAgentsPlugin(),
            OpenCodeCommandsPlugin(),
        ]
    if host == "copilot":
        from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin

        return [HooksPlugin()]
    return []


@dataclass(frozen=True)
class _NativeHost:
    """A native host nWave installs into, checked once its config directory exists.

    ``config_dir`` is resolved by the same function the host's installer plugins
    write through, so a relocated host (``CURSOR_HOME``, ``COPILOT_HOME``,
    ``OPENCODE_CONFIG_DIR``, ``PI_CONFIG_DIR`` ...) is found where it was installed.
    """

    name: str
    config_dir: Path

    @property
    def is_present(self) -> bool:
        return self.config_dir.exists()

    def verify(self, claude_dir: Path) -> list:
        """Run this host's verifiers and return their ``PluginResult`` list."""
        from scripts.install import verify_nwave

        if self.name in verify_nwave._NATIVE_PLATFORMS:
            return verify_nwave.verify_native_platform(
                self.name, claude_dir, _SilentLogger()
            )
        context = verify_nwave._make_verify_context(
            claude_dir, self.name, _SilentLogger()
        )
        return [plugin.verify(context) for plugin in _verifying_plugins(self.name)]


def _present_native_hosts() -> list[_NativeHost]:
    """Native hosts whose configuration directory exists, in report order."""
    try:
        from nwave_ai.upgrade_shell import copilot_config_dir, cursor_config_dir
        from scripts.install.plugins.opencode_common import opencode_config_dir
        from scripts.shared.install_paths import (
            codex_config_dir,
            devin_config_dir,
            omp_agent_dir,
        )
    except ImportError:
        return []

    hosts = (
        _NativeHost("codex", codex_config_dir()),
        _NativeHost("cursor", cursor_config_dir(Path.home())),
        _NativeHost("devin", devin_config_dir()),
        _NativeHost("omp", omp_agent_dir()),
        _NativeHost("opencode", opencode_config_dir()),
        _NativeHost("copilot", copilot_config_dir(Path.home())),
    )
    return [host for host in hosts if host.is_present]


def _report_native_platform_status(hosts: list[_NativeHost], claude_dir: Path) -> bool:
    """Verify and report every present native host (Codex, Cursor, Devin, OMP,
    OpenCode, Copilot).

    Human mode only: the JSON contract stays stable -- use
    verify_nwave.py --platform all --json for machine-readable native checks.

    Returns True when any native platform check fails, False otherwise.
    """
    if not hosts:
        return False
    try:
        from scripts.install.verify_nwave import format_native_results
    except ImportError:
        return False

    any_failed = False
    print()
    print("Native platforms detected:")
    for host in hosts:
        try:
            results = host.verify(claude_dir)
            if not all(r.success for r in results):
                any_failed = True
            print(format_native_results(host.name, results))
        except Exception as exc:  # best-effort, must not crash doctor
            print(f"  ⚠️  {host.name}: verification error — {exc}")
            any_failed = True
    return any_failed


#: Checks whose subject is the Claude Code profile (settings.json, shims,
#: framework directories). A native-only installation
#: never creates those files, so demanding them would fail a healthy install.
_CLAUDE_CODE_CHECKS = frozenset(
    check.name
    for check in (
        HooksRegisteredCheck,
        HookPythonPathCheck,
        FrameworkFilesCheck,
    )
)


def _handle_doctor(args: list[str]) -> int:
    """Handle 'doctor [--json] [--fix] [--target <path>] [--help]' subcommand.

    Flags handled here:
        --target <path>    diagnose <path> instead of ~/.claude/ (sets
                           CLAUDE_CONFIG_DIR for this process; see ADR-001).
                           Mirrors install/uninstall (_handle_install /
                           _handle_uninstall) so a multi-profile setup is
                           diagnosed on the profile actually named, not
                           always the default -- otherwise doctor silently
                           reports on the WRONG installation.
    """
    target, args, error = _extract_target_flag(args)
    if error is not None:
        print(f"nwave-ai: {error}", file=sys.stderr)
        return 2
    if target is not None:
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)

    json_output = False
    fix = False

    for arg in args:
        if arg in ("--help", "-h"):
            print("Usage: nwave-ai doctor [--json] [--fix] [--target <path>]")
            print()
            print("Run diagnostic checks on the nWave installation.")
            print()
            print("Options:")
            print("  --json          Emit JSON output instead of human-readable text.")
            print(
                "  --fix           Attempt to fix detected issues (not yet "
                "implemented)."
            )
            print(
                "  --target <path> Diagnose <path> instead of ~/.claude/ "
                "(sets CLAUDE_CONFIG_DIR)."
            )
            print("  --help          Show this message and exit.")
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
    native_hosts = _present_native_hosts()
    # Claude Code files are demanded only of a Claude Code installation. With
    # no Claude profile on disk and a native host installed, they belong to a
    # host that was never installed; with nothing installed at all the doctor
    # keeps reporting everything missing.
    claude_code_installed = context.claude_dir.is_dir() or not native_hosts
    results = [
        result
        for result in run_doctor(context)
        if claude_code_installed or result.check_name not in _CLAUDE_CODE_CHECKS
    ]

    if json_output:
        print(render_json(results))
    else:
        print(render_human(results))

    native_failed = not json_output and _report_native_platform_status(
        native_hosts, context.claude_dir
    )

    if any(not r.passed for r in results) or native_failed:
        return 1
    return 0


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


# Argv prefix per installer. The plugin handler appends `<action> <pkg>` to this.
_INSTALLER_COMMANDS: dict[str, tuple[str, ...]] = {
    "uv": ("uv", "tool"),
    "pipx": ("pipx",),
    "pip": ("pip",),
}

# PATH-availability hint emitted after a successful install if the plugin
# binary isn't yet on PATH. Mirrors each tool's own remediation command.
_INSTALLER_PATH_HINTS: dict[str, str] = {
    "uv": "Run `uv tool update-shell` (or restart your shell) to refresh PATH.",
    "pipx": "Restart your shell or run `pipx ensurepath`.",
    "pip": "Ensure pip's user-bin dir is on PATH (see `python -m site --user-base`).",
}


def _resolve_installer() -> tuple[list[str], str] | None:
    """Pick a Python package installer for `nwave-ai plugin install`.

    Delegates toolchain identity to the shared
    ``nwave_ai.platform.package_manager.detect_pm`` (including honoring the
    ``NWAVE_INSTALLER`` override). When the detector cannot identify the owner,
    falls back to a uv-first PATH scan.

    Returns:
        ``(cmd_prefix, tool_name)`` where ``cmd_prefix`` is the argv prefix
        before ``<action> <pkg>``, or ``None`` if no installer is available.
    """
    import shutil

    from nwave_ai.platform.package_manager import (
        detect_pm,
    )

    # 1 + 2: explicit override or the manager that owns this interpreter.
    pm = detect_pm(Path(sys.executable))
    if pm != "unknown" and shutil.which(pm):
        return (list(_INSTALLER_COMMANDS[pm]), pm)

    # 3: uv-first PATH scan when ownership is indeterminate.
    for tool in ("uv", "pipx", "pip"):
        if shutil.which(tool):
            return (list(_INSTALLER_COMMANDS[tool]), tool)
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
            "No installer (uv, pipx, or pip) is available on PATH. "
            "Install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`) "
            "or pipx and retry.",
            file=sys.stderr,
        )
        return 1
    cmd_prefix, tool = installer

    action = "install" if sub == "install" else "uninstall"
    cmd = [*cmd_prefix, action]
    # `pip uninstall` prompts for confirmation by default; -y keeps it
    # non-interactive so it can't hang when stdin is not a TTY (CI, subagents).
    # uv tool / pipx uninstall are non-interactive already.
    if tool == "pip" and action == "uninstall":
        cmd.append("-y")
    cmd.append(pkg)
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=False)
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
            hint = _INSTALLER_PATH_HINTS.get(tool, "")
            print(
                f"Warning: {tool} reported success but '{cli_name}' is not on "
                f"PATH yet. {hint}",
                file=sys.stderr,
            )
            return 0
        print(f"OK: {cli_name} installed and on PATH.")
    else:
        print(f"OK: {pkg} uninstalled.")
    return 0


_MODEL_USAGE = (
    "Usage: nwave-ai model set --provider {codex,claude} --model MODEL "
    "[--role ROLE [--competence COMPETENCE]] [--project]"
)


def _handle_model(args: list[str]) -> int:
    """Publish one complete provider/model declaration through ``ConfigWriter``."""
    if not args or args[0] in {"--help", "-h", "help"}:
        print(_MODEL_USAGE)
        print()
        print("Without --project the global default is updated.")
        print("With --role, update that role instead of the tier default.")
        return 0 if args else 1
    if args[0] != "set":
        print(_MODEL_USAGE, file=sys.stderr)
        return 2
    if len(args) == 2 and args[1] in {"--help", "-h", "help"}:
        print(_MODEL_USAGE)
        print()
        print("Without --project the global default is updated.")
        print("With --role, update that role instead of the tier default.")
        return 0

    provider: str | None = None
    model: str | None = None
    role: str | None = None
    competence: str | None = None
    project = False
    index = 1
    while index < len(args):
        option = args[index]
        if option == "--project":
            if project:
                print(_MODEL_USAGE, file=sys.stderr)
                return 2
            project = True
            index += 1
            continue
        if option in {"--provider", "--model", "--role", "--competence"}:
            if index + 1 >= len(args):
                print(_MODEL_USAGE, file=sys.stderr)
                return 2
            value = args[index + 1]
            if option == "--provider" and provider is None:
                provider = value
            elif option == "--model" and model is None:
                model = value
            elif option == "--role" and role is None:
                role = value
            elif option == "--competence" and competence is None:
                competence = value
            else:
                print(_MODEL_USAGE, file=sys.stderr)
                return 2
            index += 2
            continue
        print(_MODEL_USAGE, file=sys.stderr)
        return 2

    if competence is not None and role is None:
        print(
            "WHAT: --competence requires --role. HOW: " + _MODEL_USAGE,
            file=sys.stderr,
        )
        return 2

    if (
        provider not in {"codex", "claude"}
        or not isinstance(model, str)
        or not model.strip()
    ):
        print(
            "WHAT: model selection requires provider codex|claude and a non-empty model. "
            f"HOW: {_MODEL_USAGE}",
            file=sys.stderr,
        )
        return 2
    if role is not None and not role.strip():
        print("WHAT: --role must be non-empty. HOW: " + _MODEL_USAGE, file=sys.stderr)
        return 2
    role_key = role
    if role is not None and competence is not None:
        from nwave_ai.platform.roles import qualify_role_id

        try:
            role_key = qualify_role_id(role, competence)
        except ValueError as error:
            print(
                f"WHAT: --competence is invalid. WHY: {error}. HOW: {_MODEL_USAGE}",
                file=sys.stderr,
            )
            return 2
    if role is not None:
        # A role key is not free-form configuration: a typo would otherwise
        # persist an override no invocation can ever select. Resolve it before
        # importing or calling the mutating writer, so refusal preserves both
        # unified config bytes exactly.
        from nwave_ai.platform.capability import (
            ClaimRegister,
            resolve_declared_capability,
        )

        capability = resolve_declared_capability(role, repo_root=Path.cwd())
        if capability.register is ClaimRegister.UNKNOWN or capability.spec_path is None:
            print(
                "WHAT: --role must name one readable published agent specification. "
                f"HOW: correct {role!r} and retry.\n{_MODEL_USAGE}",
                file=sys.stderr,
            )
            return 2

    try:
        config_dir = _require_mutating_config_dir()
    except ValueError as error:
        return _refuse_mutating_location(error)

    # Import only when this mutating command is selected.  Version/help remain
    # usable in a minimal installed runtime before the bundled DES layer loads.
    from nwave_ai.platform.config_writer import (
        ConfigMigrationError,
        ConfigWriter,
    )

    pair = {"provider": provider, "model": model}
    # Share the same NWAVE_AGENTS_HOME-aware global authority that NWaveConfig
    # reads. A bare Path.home() here would write a second global tier when an
    # operator deliberately redirected the nWave home.
    writer = ConfigWriter(home_dir=config_dir.parent, repo_root=Path.cwd())

    def mutate(document: dict[str, object]) -> None:
        current = document.get("model_runtime")
        runtime = dict(current) if isinstance(current, dict) else {}
        if role is None:
            runtime["default"] = pair
        else:
            roles = runtime.get("roles")
            role_map = dict(roles) if isinstance(roles, dict) else {}
            role_map[role_key] = pair
            runtime["roles"] = role_map
        document["model_runtime"] = runtime

    try:
        if project:
            writer.update_repo(mutate)
            target = writer.repo_path
        else:
            writer.update_global(mutate)
            target = writer.global_path
    except ConfigMigrationError as error:
        print(
            f"WHAT: model selection was not written. WHY: {error}. "
            "HOW: repair the unified config and retry.",
            file=sys.stderr,
        )
        return 1
    scope = f"role {role_key}" if role_key is not None else "default"
    print(f"Model runtime {scope} set to {provider}/{model} in {target}.")
    return 0


def _print_usage(version: str) -> int:
    print(f"nwave-ai {version}")
    print()
    print("Usage: nwave-ai <command> [options]")
    print()
    print("Commands:")
    print("  install        Install nWave framework to supported tool configs")
    print("  uninstall      Remove nWave framework from supported tool configs")
    print("  doctor         Run diagnostics on the nWave installation")
    print("  attribution    Toggle commit attribution (on/off/status)")
    print("  model          Select the provider and model for nWave roles")
    print("  outcomes       Register / check shipped outcomes (Tier-1 collision)")
    print("  plugin         Manage tool plugins (install/uninstall/list)")
    print("  project        Enable, disable, or configure nWave for this project")
    print("  mode           Set the global activation mode (all/opt-in)")
    print(
        "  status         Show this project's effective configuration and host assets"
    )
    print("  completion     Print a shell-completion script (bash/zsh)")
    print("  update --check Discover the latest stable public release")
    print("  update consent <check|install> <on|off> Set separate startup permissions")
    print("        install on requires --confirm-old-sessions-closed the first time;")
    print(
        "        sessions started before the activity registry rest on that confirmation"
    )
    print(
        "  update sessions [close KEY --confirm-closed] List or close registered sessions"
    )
    print("  update --recover --yes --confirm-stopped Resume verified incomplete sync")
    print(
        "  migrate-artifacts [--dry-run|--apply] --root PATH  Migrate legacy artifacts"
    )
    print("  update consent controlled-launch on --confirm-controlled-launch | off")
    print(
        "  run HOST -- ARGS  Controlled startup for claude-code, codex, opencode, copilot"
    )
    print("  version        Show nwave-ai version")
    print()
    print("Install options:")
    from scripts.install.install_nwave import _explicit_platform_names

    print(f"  --platform <tool>  Target agentic tool: {_explicit_platform_names()}")
    print("  --dry-run       Preview without making changes")
    print("  --backup-only   Create backup only")
    print("  --restore       Restore from backup")
    print()
    print("Example:")
    print("  nwave-ai install")
    return 0


# ---------------------------------------------------------------------------
# Activation gating verbs (EXTEND, DDD-12). `project enable|disable`,
# `mode all|opt-in`, `status`. `main_with_argv(argv)` is the testable entry
# that dispatches the same way `main()` does but takes argv explicitly (so
# acceptance tests need not patch sys.argv). `status` is read-only (no write
# surface, Principle 12).
# ---------------------------------------------------------------------------


# Hosts synced on every `project enable|disable` — one parameterized path
# (`_sync_guidance_section_for_host`) called once per host, never a
# per-host branch/copy of the sync logic.
_GUIDANCE_HOSTS = ("claude", "codex")


def _sync_guidance_section_for_host(
    host: str, action: str, project_root: Path, *, assume_yes: bool
) -> None:
    """Inject (enable) or remove (disable) the managed beta section for `host`.

    Modifying the user's project guidance file is a durable, user-facing change,
    so `enable` asks for consent first (Ale 2026-06-30: "ci vuole la richiesta
    all'utente"). `--yes` (or any non-interactive context with `--yes`) bypasses
    the prompt; a non-interactive context WITHOUT `--yes` skips injection and
    prints how to add it. Removal of our own marker-bounded block on `disable`
    needs no prompt. Fail-open throughout: a section fault never breaks the
    activation toggle.
    """
    from scripts.install.project_claude_section import (
        HOSTS,
        inject_managed_section,
        load_section_content,
        remove_managed_section,
    )

    target_md = project_root / HOSTS[host].filename

    if action == "disable":
        try:
            outcome = remove_managed_section(target_md)
        except OSError as exc:
            print(f"  (could not update {target_md}: {exc})", file=sys.stderr)
            return
        if outcome == "removed-file":
            print(
                f"Removed the nWave beta section (and the now-empty {target_md.name})."
            )
        elif outcome == "removed-section":
            print(f"Removed the nWave beta section from {target_md.name}.")
        return

    # action == "enable"
    try:
        content = load_section_content(_get_project_root(), host=host)
        # Templates live with the installed distribution, while the generated
        # region's configuration belongs to the caller's project.  Reproject
        # the loaded template against that caller root so an install invoked
        # from a project never publishes the distribution checkout's config.
        from nwave_ai.platform.regions import project_asset

        content = project_asset(target_md, content, project_root).projected_text
    except OSError:
        # Template missing (unusual) — never block the toggle on it.
        return

    if assume_yes:
        consent = True
    elif sys.stdin.isatty():
        answer = input(
            f"Add the nWave beta-feedback guidance section to ./{target_md.name}? "
            "(removable later with `nwave-ai project disable`) [Y/n] "
        )
        consent = answer.strip().lower() in ("", "y", "yes")
    else:
        consent = False

    if not consent:
        print(
            f"Skipped the {target_md.name} beta section. Add it anytime with "
            "`nwave-ai project enable --yes` from this project."
        )
        return

    try:
        outcome = inject_managed_section(target_md, content)
    except OSError as exc:
        print(f"  (could not update {target_md}: {exc})", file=sys.stderr)
        return
    verb = {"created": "Created", "appended": "Added", "updated": "Refreshed"}[outcome]
    print(f"{verb} the nWave beta section in {target_md.name}.")


def _sync_project_claude_section(
    action: str, project_root: Path, *, assume_yes: bool
) -> None:
    """Sync the managed beta section into every supported host's guidance file."""
    for host in _GUIDANCE_HOSTS:
        _sync_guidance_section_for_host(
            host, action, project_root, assume_yes=assume_yes
        )


_PROJECT_USAGE = (
    "Usage: nwave-ai project <enable|disable> [--yes]\n"
    "       nwave-ai project set <enabled|verbosity|attribution> <value> [--yes]\n"
    "       nwave-ai project feature-document <feature-id> <discuss|design|distill|devops> <path>\n"
    "           (one feature's document destination, under docs/feature/<feature-id>/)\n"
    "       nwave-ai project feature-template <discuss|design|distill|devops> <template-with-{feature}>\n"
    "           (project-wide default for every feature; project keys documents.<wave> stay project-only)"
)


def _project_set_value(field: str, raw_value: str) -> bool | str | None:
    """Parse the closed public type surface for a project override."""
    if field == "enabled":
        return {"true": True, "false": False}.get(raw_value)
    if field == "verbosity" and raw_value in ("terse", "standard", "verbose"):
        return raw_value
    if field == "attribution":
        return {"on": True, "off": False}.get(raw_value)
    return None


def _handle_project(args: list[str]) -> int:
    """Handle project activation and typed repository configuration overrides.

    On `enable`, also offers to inject the managed beta-feedback section into each
    supported host's guidance file (CLAUDE.md, AGENTS.md; consent-gated per host,
    `--yes` bypasses). On `disable`, removes it from all of them.

    Fail-closed argument boundary: `--help`/`-h` anywhere in ``args`` prints
    usage and returns 0 without touching the filesystem, and anything left
    over besides the action and `--yes` (unknown option, extra positional)
    is rejected with usage + nonzero -- both checked BEFORE any write, so a
    malformed or informational invocation can never mutate the project.
    """
    if any(a in ("--help", "-h") for a in args):
        print(_PROJECT_USAGE)
        return 0
    assume_yes = "--yes" in args
    positional = [a for a in args if a != "--yes"]
    if args.count("--yes") > 1:
        print(_PROJECT_USAGE, file=sys.stderr)
        return 1

    if positional[:1] in (["feature-document"], ["feature-template"]):
        expected = 4 if positional[0] == "feature-document" else 3
        if len(positional) != expected:
            print(_PROJECT_USAGE, file=sys.stderr)
            return 1
        try:
            _require_mutating_config_dir()
            from nwave_ai.platform.config_writer import ConfigWriter

            writer = ConfigWriter(
                home_dir=_require_mutating_config_dir().parent, repo_root=Path.cwd()
            )
            if positional[0] == "feature-document":
                writer.set_feature_document(*positional[1:])
            else:
                writer.set_feature_template(*positional[1:])
        except Exception as exc:
            print(
                "WHAT: feature document configuration was not written. "
                f"WHY: {exc}. HOW: use a safe path under the feature directory "
                "(or a template containing {feature}) and retry.",
                file=sys.stderr,
            )
            return 1
        print(f"nWave feature configuration set: {' '.join(positional[1:])}.")
        return 0

    if positional[:1] == ["set"]:
        if len(positional) != 3:
            print(_PROJECT_USAGE, file=sys.stderr)
            return 1
        field, raw_value = positional[1:]
        value = _project_set_value(field, raw_value)
        if value is None:
            print(_PROJECT_USAGE, file=sys.stderr)
            return 1
        project_root = Path.cwd()
        if not _write_project_override(project_root, field=field, value=value):
            return 1
        print(f"nWave project override set: {field}={raw_value}.")
        # The configuration commit is the success boundary.  Rendered guidance
        # is refreshed only afterwards, through its existing merged projection.
        _sync_project_claude_section("enable", project_root, assume_yes=assume_yes)
        return 0

    if len(positional) != 1 or positional[0] not in ("enable", "disable"):
        print(_PROJECT_USAGE, file=sys.stderr)
        return 1
    from nwave_ai.platform.gitignore import ProjectGitignoreService

    action = positional[0]
    project_root = Path.cwd()
    if not _write_marker(project_root, enabled=action == "enable"):
        return 1
    ProjectGitignoreService().fix_gitignore(project_root=project_root)
    state = "enabled" if action == "enable" else "disabled (sticky opt-out)"
    print(f"nWave activation for this project: {state}.")
    _sync_project_claude_section(action, project_root, assume_yes=assume_yes)
    return 0


def _handle_mode(args: list[str]) -> int:
    """Handle 'mode all|opt-in' — set the global activation mode."""
    if not args or args[0] not in ("all", "opt-in"):
        print("Usage: nwave-ai mode <all|opt-in>", file=sys.stderr)
        return 1
    try:
        config_dir = _require_mutating_config_dir()
    except ValueError as error:
        return _refuse_mutating_location(error)
    from nwave_ai.platform.config_writer import (
        ConfigMigrationError,
        ConfigWriter,
    )

    def set_mode(document: dict) -> None:
        activation = document.get("activation")
        activation = dict(activation) if isinstance(activation, dict) else {}
        activation["mode"] = args[0]
        document["activation"] = activation

    try:
        ConfigWriter(home_dir=config_dir.parent, repo_root=Path.cwd()).update_global(
            set_mode
        )
    except ConfigMigrationError as error:
        print(
            f"WHAT: activation mode was not written. WHY: {error}. "
            "HOW: repair the named configuration file and retry.",
            file=sys.stderr,
        )
        return 1
    print(f"Global nWave activation mode set to '{args[0]}'.")
    return 0


def _handle_status(args: list[str]) -> int:
    """Show the selected project's effective settings without writes or network."""
    from nwave_ai.status import render_status

    try:
        report = render_status(Path.cwd())
    except ValueError as exc:
        print(
            f"WHAT: status unavailable. WHY: {exc}. HOW: fix the selected home override.",
            file=sys.stderr,
        )
        return 1
    print(report)
    return 0


def _handle_completion(args: list[str]) -> int:
    """Handle 'completion <bash|zsh>' — print the generated shell-completion script.

    Reaches the spec-driven generator (``nwave_ai.completion.generate_completion``)
    that was otherwise unreachable from the CLI. A missing or unsupported shell
    prints usage to stderr and exits nonzero.
    """
    from nwave_ai.completion import generate_completion

    if not args or args[0] in ("--help", "-h"):
        print("Usage: nwave-ai completion <bash|zsh>", file=sys.stderr)
        return 1
    try:
        print(generate_completion(args[0]))
    except ValueError:
        print(f"Unsupported completion shell: {args[0]!r}", file=sys.stderr)
        print("Usage: nwave-ai completion <bash|zsh>", file=sys.stderr)
        return 1
    return 0


def _observe_project_activation(project_root: Path) -> bool:
    """Read the canonical project declaration through the activation policy."""
    from nwave_ai.platform.activation import resolve_activation
    from nwave_ai.platform.config import NWaveConfig

    config = NWaveConfig(cwd=project_root)
    return resolve_activation(config.enabled_for_repo, config.activation_mode)


def _write_marker(project_root: Path, *, enabled: bool) -> bool:
    """Atomically publish the canonical project activation declaration."""
    try:
        home_dir = _require_mutating_config_dir().parent
    except ValueError as error:
        _refuse_mutating_location(error)
        return False
    try:
        from nwave_ai.platform.config_writer import ConfigWriter

        writer = ConfigWriter(home_dir=home_dir, repo_root=project_root)
        writer.update_repo(lambda document: document.update(enabled=enabled))
    except Exception as exc:
        print(
            "WHAT: project activation could not publish its canonical configuration. "
            f"WHY: {exc}. HOW: repair the .nwave directory and retry.",
            file=sys.stderr,
        )
        return False

    try:
        observed = _observe_project_activation(project_root)
    except Exception as exc:
        print(
            "WHAT: project activation could not verify its canonical configuration. "
            f"WHY: {exc}. HOW: repair the .nwave configuration and retry.",
            file=sys.stderr,
        )
        return False
    if observed != enabled:
        print(
            "WHAT: project activation state did not match the requested state. "
            f"WHY: observed {observed!r} after publication. "
            "HOW: resolve concurrent changes to .nwave/config.json and retry.",
            file=sys.stderr,
        )
        return False
    return True


def _write_project_override(
    project_root: Path, *, field: str, value: bool | str
) -> bool:
    """Publish one typed project override through the sole repository writer."""
    try:
        home_dir = _require_mutating_config_dir().parent
    except ValueError as error:
        _refuse_mutating_location(error)
        return False
    try:
        from nwave_ai.platform.config_writer import ConfigWriter

        writer = ConfigWriter(home_dir=home_dir, repo_root=project_root)
        writer.set_repo_override(field, value)
    except Exception as exc:
        print(
            "WHAT: project configuration could not publish its typed override. "
            f"WHY: {exc}. HOW: repair the .nwave configuration and retry.",
            file=sys.stderr,
        )
        return False
    return True


_ACTIVATION_HANDLERS = {
    "project": _handle_project,
    "mode": _handle_mode,
    "status": _handle_status,
    "completion": _handle_completion,
}


def main_with_argv(argv: list[str]) -> int:
    """Dispatch a CLI invocation from an explicit argv (testable entry).

    ``argv`` excludes the program name, e.g. ``["project", "enable"]`` or
    ``["mode", "opt-in"]`` or ``["status"]`` or ``["completion", "bash"]``.
    Returns the process exit code (0 on success; nonzero + usage text on stderr
    for bad args).
    """
    if not argv:
        print("Usage: nwave-ai <project|mode|status|completion> ...", file=sys.stderr)
        return 1
    handler = _ACTIVATION_HANDLERS.get(argv[0])
    if handler is None:
        print(f"Unknown command: {argv[0]}", file=sys.stderr)
        print("Run 'nwave-ai --help' for usage.", file=sys.stderr)
        return 1
    return handler(argv[1:])


def main() -> int:
    """CLI entry point for nwave-ai."""
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        try:
            version = nwave_ai.__version__
        except VersionResolutionError as exc:
            return _refuse_version_resolution(exc)
        return _print_usage(version)

    if sys.argv[1] in ("--version", "-V"):
        try:
            version = nwave_ai.__version__
        except VersionResolutionError as exc:
            return _refuse_version_resolution(exc)
        print(f"nwave-ai {version}")
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
    elif command == "update":
        return _handle_update(sys.argv[2:])
    elif command == "migrate-artifacts":
        from nwave_ai.update.migrate_artifacts import main as migrate_main

        return migrate_main(sys.argv[2:])
    elif command == "run":
        return _handle_run(sys.argv[2:])
    elif command == "outcomes":
        from nwave_ai.outcomes.cli import handle_outcomes

        return handle_outcomes(sys.argv[2:])
    elif command == "plugin":
        return _handle_plugin(sys.argv[2:])
    elif command == "model":
        return _handle_model(sys.argv[2:])
    elif command in ("project", "mode", "status", "completion"):
        return main_with_argv(sys.argv[1:])
    elif command == "version":
        try:
            version = nwave_ai.__version__
        except VersionResolutionError as exc:
            return _refuse_version_resolution(exc)
        print(f"nwave-ai {version}")
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'nwave-ai --help' for usage.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
