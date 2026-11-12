"""nwave-ai CLI: thin wrapper around nWave install/uninstall scripts."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
from nwave_ai.platform.result import Failure, Success  # noqa: E402
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


_JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
_JEV_PRIVACY_URL = "https://github.com/nWave-ai/nWave/blob/main/PRIVACY.md"
_JEV_SWITCH_LINE = '"jev": "unauthorized"'


def _jev_machine_defect(machine: str | None, problem: str | None) -> str | None:
    """Pure: why the machine-wide Jev value cannot be used, or None when it can."""
    from nwave_ai.platform.config_writer import ConfigWriter

    if problem is not None:
        return f"the machine-wide file could not be read: {problem}"
    if machine is None or machine in ConfigWriter.JEV_VALUES:
        return None
    return f"the machine-wide jev value {machine!r} is not a Jev choice"


def _machine_jev_rule(machine: str | None, problem: str | None) -> tuple[str, str]:
    """Pure: the value a project gets when nobody answers, and where that value comes from.

    A machine-wide refusal is kept, so an install default can never loosen it. An absent
    machine-wide value gives the declared default. A value that is not a Jev choice, or a
    file that cannot be read, fails closed to unauthorized.
    """
    from nwave_ai.platform.config_writer import ConfigWriter

    if _jev_machine_defect(machine, problem) is not None:
        return (
            ConfigWriter.JEV_UNAUTHORIZED,
            "the machine-wide setting, which fails closed",
        )
    if machine is None:
        return ConfigWriter.JEV_DECLARED_DEFAULT, "the declared default"
    if machine == ConfigWriter.JEV_UNAUTHORIZED:
        return machine, "your machine-wide refusal"
    return machine, "your machine-wide setting"


def _jev_question(machine: str | None, problem: str | None) -> str:
    """Pure: the consent question shown on a terminal, stating the machine-wide value it keeps."""
    defect = _jev_machine_defect(machine, problem)
    if defect is not None:
        setting = (
            f"Machine-wide Jev setting: {defect}. An empty answer refuses Jev here. "
        )
    elif machine is None:
        setting = ""
    else:
        setting = f"Machine-wide Jev setting: {machine}. An empty answer keeps it. "
    return (
        setting
        + f"Jev is a remote service at {_JEV_ENDPOINT}. It receives the typed questions "
        "and the task state nWave sends, never secrets, personal data, source-blind "
        "material or secret-bearing logs. "
        f"Allow Jev for this project? [Y/n] (see {_JEV_PRIVACY_URL}) "
    )


def _jev_answer(answer: str, default: str) -> tuple[str, str]:
    """Pure: the value an answer records and how it was recorded, as enter or answer.

    An empty answer keeps the default. y or yes allows Jev; any other text refuses it.
    """
    from nwave_ai.platform.config_writer import ConfigWriter

    text = answer.strip().lower()
    if text == "":
        return default, "enter"
    if text in ("y", "yes"):
        return ConfigWriter.JEV_AUTHORIZED, "answer"
    return ConfigWriter.JEV_UNAUTHORIZED, "answer"


def _jev_origin(how: str, choice: str, why: str) -> str:
    """Pure: the sentence saying whether a person chose the recorded value, and from what."""
    if how == "answer":
        return f"you answered, so {choice} is your choice"
    if how == "enter":
        return f"you pressed Enter, so {choice} is recorded from {why}"
    return f"nWave wrote {choice} from {why}; you did not choose it for this project"


def _jev_notice(config_path: Path, origin: str) -> str:
    """Pure: the line printed after a value is recorded, naming where the value came from."""
    return (
        f"Jev for this project ({config_path}): {origin}. Jev is external processing, "
        f"not telemetry; see {_JEV_PRIVACY_URL}. To switch it off for this project, "
        f"set {_JEV_SWITCH_LINE} in that file."
    )


def _ask_jev(machine: str | None, problem: str | None, default: str) -> tuple[str, str]:
    """Shell: ask on the terminal; end of input is no answer and records the default."""
    try:
        answer = input(_jev_question(machine, problem))
    except EOFError:
        return default, "written"
    return _jev_answer(answer, default)


def _read_machine_jev(writer) -> tuple[str | None, str | None]:
    """Shell: the machine-wide jev value, or the reason the machine-wide file cannot be read."""
    from nwave_ai.platform.config_writer import ConfigMigrationError

    try:
        return writer.machine_jev(), None
    except ConfigMigrationError as error:
        return None, str(error)


def _declare_project_jev(
    project_root: Path, home_dir: Path, *, interactive: bool
) -> None:
    """Shell: record the project's Jev choice after a successful install; never fails it.

    A project that already holds a jev key is left alone and never asked about. The
    machine-wide setting is respected: a refusal there is kept by the default and shown in the
    question. A machine-wide value that cannot be used fails closed to unauthorized with a
    WHAT, WHY, HOW line on stderr. Three outcomes: a refusal writes nothing; a failure before
    the write writes nothing; a write that cannot be confirmed afterwards has written the entry,
    and the WHAT line says it was written.
    """
    from nwave_ai.platform.config_writer import ConfigWriter
    from nwave_ai.platform.gitignore import ensure_nwave_gitignore

    writer = ConfigWriter(home_dir=home_dir, repo_root=project_root)
    try:
        if writer.repo_declares_jev():
            return
        machine, problem = _read_machine_jev(writer)
        default, why = _machine_jev_rule(machine, problem)
        choice, how = (
            _ask_jev(machine, problem, default) if interactive else (default, "written")
        )
        folder_created = not writer.repo_path.parent.exists()
        declared = writer.declare_repo_jev(choice)
        if declared and folder_created:
            # The installer created this .nwave folder for the declaration, so it owns the folder,
            # the same ownership mark project enable writes; uninstall relies on that mark.
            ensure_nwave_gitignore(writer.repo_path)
    except Exception as exc:
        from nwave_ai.platform.config_writer import JevDeclarationUnverifiedError

        if isinstance(exc, JevDeclarationUnverifiedError):
            outcome = f"the Jev choice for {project_root} was written but could not be confirmed"
            remedy = "check the project's .nwave/config.json for the jev entry"
        else:
            outcome = f"the Jev choice for {project_root} was not recorded"
            remedy = "fix the reported problem, then rerun nwave-ai install"
        print(f"WHAT: {outcome}. WHY: {exc}. HOW: {remedy}.", file=sys.stderr)
        return
    defect = _jev_machine_defect(machine, problem)
    if defect is not None and how != "answer":
        print(
            f"WHAT: the machine-wide Jev setting was not used for {project_root}. "
            f"WHY: {defect}. HOW: correct the machine-wide configuration, or set jev in "
            "this project's .nwave/config.json; nWave wrote unauthorized and will not "
            "rewrite the project's value.",
            file=sys.stderr,
        )
    if declared:
        print(_jev_notice(writer.repo_path, _jev_origin(how, choice, why)))


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

    # The project's Jev choice is recorded only after a successful install. A terminal
    # answers it; a restore or backup-only run writes no new project state.
    if "--restore" not in args and "--backup-only" not in args:
        _declare_project_jev(
            caller_project_root,
            config_dir.parent,
            interactive=not non_interactive,
        )

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


_RIGOR_USAGE = (
    "Usage: nwave-ai rigor [--show] [--yes] [--models keep | --model-set "
    "GROUP_OR_ROLE=PROVIDER/MODEL ...] [--review-rounds 1-5|current] "
    "[--examine-level quick|standard|extended|current] "
    "[--documents yes|no|keep [--document-language LANG]] "
    "[--hosts HOST[,HOST...]|none|keep]"
)


def _rigor_agents_home() -> Path:
    import os

    override = os.environ.get("NWAVE_AGENTS_HOME")
    return Path(override).expanduser() if override else Path.home()


def _rigor_published_roles() -> dict[str, dict[str, str]]:
    """Published role names with their declared tools and model, from specs.

    The roles are read from the nWave checkout surfaces (``nWave/agents`` in
    the project and the agents home) and from the installed agent surfaces
    (``~/.claude/agents/nw`` subagent files and ``~/.codex/agents`` TOML
    files), so the command works in the developer's own repository too.
    """
    import re

    published: dict[str, dict[str, str]] = {}
    roots = [
        (Path.cwd() / "nWave" / "agents", "*.md", "markdown"),
        (_rigor_agents_home() / "nWave" / "agents", "*.md", "markdown"),
        (_rigor_agents_home() / ".claude" / "agents" / "nw", "*.md", "markdown"),
        (_rigor_agents_home() / ".codex" / "agents", "*.toml", "toml"),
    ]
    for root, pattern, kind in roots:
        if not root.is_dir():
            continue
        for spec in sorted(root.glob(pattern)):
            try:
                text = spec.read_text(encoding="utf-8")
            except OSError:
                continue
            if kind == "markdown":
                name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
                if name_match is None:
                    continue
                name = name_match.group(1).strip()
                tools_match = re.search(r"^tools:\s*(.+)$", text, re.MULTILINE)
                model_match = re.search(r"^model:\s*(.+)$", text, re.MULTILINE)
                published[name] = {
                    "tools": tools_match.group(1).strip() if tools_match else "",
                    "model": model_match.group(1).strip() if model_match else "",
                }
            else:
                name_match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
                if name_match is None:
                    continue
                published.setdefault(
                    name_match.group(1).strip(),
                    {
                        "tools": "",
                        "model": "",
                    },
                )
    return published


def _rigor_read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read one config file; (document, None) or (None, error message)."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}, None
    except OSError as error:
        return None, str(error)
    import json as _json

    try:
        document = _json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        return None, f"{path} is unreadable JSON: {error}"
    if not isinstance(document, dict):
        return None, f"{path} is unreadable JSON: expected an object"
    return document, None


def _rigor_tiers(
    project_path: Path, global_path: Path
) -> tuple[tuple[dict[str, Any], dict[str, Any]] | None, str | None]:
    project, project_error = _rigor_read_json(project_path)
    if project_error is not None or project is None:
        return None, project_error
    global_tier, global_error = _rigor_read_json(global_path)
    if global_error is not None or global_tier is None:
        return None, global_error
    return (project, global_tier), None


def _rigor_print_refusal(refusal: Any, code: int = 2) -> int:
    print(refusal.render(), file=sys.stderr)
    return code


def _handle_rigor(args: list[str]) -> int:
    """Choose this project's quality scope: models per role, rounds, documents.

    Pure decisions live in rigor_core and rigor_hosts; this shell only reads,
    prints, prompts and applies atomic writes.
    """
    import os

    from nwave_ai.platform import rigor_core, rigor_hosts

    parsed_options = rigor_core.parse_options(tuple(args))
    if isinstance(parsed_options, Failure):
        what = parsed_options.error.render()
        print(f"{what}\n{_RIGOR_USAGE}", file=sys.stderr)
        return 2
    options = parsed_options.unwrap()
    show = options.show
    yes = options.yes
    model_sets = options.model_sets
    review_rounds = options.review_rounds
    documents = options.documents
    document_language = options.document_language
    hosts = options.hosts

    repo_root = Path.cwd()
    project_path = repo_root / ".nwave" / "config.json"
    global_path = _rigor_agents_home() / ".nwave" / "config.json"
    tiers, tier_error = _rigor_tiers(project_path, global_path)
    if tiers is None:
        return _rigor_print_refusal(
            rigor_core.Refusal(
                tier_error or "unknown config read failure",
                "A corrupt file would lose keys the command does not own.",
                "Restore the file from a copy or fix the JSON, then rerun; "
                "nothing was written.",
            )
        )
    repo_tier, global_tier = tiers
    published = _rigor_published_roles()
    published_tools = {name: entry["tools"] for name, entry in published.items()}

    examine_resolved = rigor_core.resolved_examine_level(repo_tier, global_tier)
    if isinstance(examine_resolved, Failure):
        return _rigor_print_refusal(examine_resolved.error)
    effective = rigor_core.EffectiveScope(
        roles=tuple(
            (
                role,
                rigor_core.resolved_role_model(
                    role,
                    repo_tier,
                    global_tier,
                    published.get(role, {}).get("model", ""),
                ),
            )
            for role in sorted(published_tools)
        ),
        review_rounds=rigor_core.resolved_review_rounds(repo_tier, global_tier),
        documents=rigor_core.resolved_documents(repo_tier, global_tier),
        examine_level=examine_resolved.unwrap(),
    )

    if show:
        for line in rigor_core.show_lines(effective):
            print(line)
        return 0

    def can_ask() -> bool:
        try:
            if sys.stdin is None or sys.stdin.isatty():
                return True
            # A pipe or redirected stdin is readable; pytest's stdin raises.
            sys.stdin.readable()

            probe = sys.stdin.readline(0)
            return isinstance(probe, str)
        except (OSError, ValueError, AttributeError):
            return False

    model_facts: tuple[rigor_core.ModelFact, ...] | None = None
    if model_sets is not None:
        facts: list[rigor_core.ModelFact] = []
        for token in model_sets:
            parsed = rigor_core.parse_model_set(token, set(published_tools))
            if isinstance(parsed, Failure):
                return _rigor_print_refusal(parsed.error)
            facts.append(parsed.unwrap())
        model_facts = tuple(facts)

    rounds_value: int | str | None = None
    if review_rounds is not None:
        effective_rounds, _ = effective.review_rounds
        parsed_rounds = rigor_core.parse_review_rounds(review_rounds, effective_rounds)
        if isinstance(parsed_rounds, Failure):
            return _rigor_print_refusal(parsed_rounds.error)
        rounds_value = (
            "current" if review_rounds == "current" else parsed_rounds.unwrap()
        )

    if documents is not None:
        parsed_documents = rigor_core.parse_documents(documents)
        if isinstance(parsed_documents, Failure):
            return _rigor_print_refusal(parsed_documents.error)

    examine_answer: str | None = None
    if options.examine_level is not None:
        parsed_examine = rigor_core.parse_examine_level(options.examine_level)
        if isinstance(parsed_examine, Failure):
            refusal = parsed_examine.error
            return _rigor_print_refusal(
                rigor_core.Refusal(
                    refusal.what,
                    refusal.why,
                    "run the command again with --examine-level quick, standard or "
                    "extended. Use current to write nothing.",
                )
            )
        examine_answer = parsed_examine.unwrap()

    def ask(prompt: str) -> str | None:
        print(prompt, end="", flush=True)
        try:
            line = sys.stdin.readline()
        except (OSError, ValueError, AttributeError):
            return None
        return line.strip() if line else None

    def ask_until_valid(prompt: str, parse: Any) -> Any:
        """Ask again until the answer parses; None when the input ends first.

        A wrong answer prints its refusal (WHAT, WHY, HOW) and asks the same
        question again; the command itself never ends on a wrong answer.
        """
        while True:
            answer = ask(prompt)
            if answer is None:
                return None
            parsed = parse(answer)
            if isinstance(parsed, Failure):
                print(parsed.error.render(), file=sys.stderr)
                continue
            return parsed.unwrap()

    answers_models = model_facts
    answers_rounds = rounds_value
    answers_documents = documents
    answers_hosts: str | None = None
    if hosts is not None:
        parsed_hosts = rigor_core.parse_hosts_answer(
            hosts, tuple(rigor_hosts.DECLARED_HOST_TARGETS)
        )
        if isinstance(parsed_hosts, Failure):
            return _rigor_print_refusal(parsed_hosts.error)
        answers_hosts = parsed_hosts.unwrap()

    interactive = can_ask()
    if not yes:
        unanswered = [
            name
            for name, value in (
                ("--models", answers_models),
                ("--review-rounds", answers_rounds),
                ("--documents", answers_documents),
                ("--hosts", answers_hosts),
            )
            if value is None
        ]
        if unanswered and not interactive:
            return _rigor_print_refusal(
                rigor_core.Refusal(
                    "Answers are missing for "
                    + ", ".join(unanswered)
                    + ", and no terminal is available to ask.",
                    "A script cannot be asked questions; an unanswered question "
                    "would silently keep the current value.",
                    "Supply every option (" + ", ".join(unanswered) + ") or run "
                    "the command on a terminal.",
                )
            )
        if unanswered:
            known_hosts = tuple(rigor_hosts.DECLARED_HOST_TARGETS)
            language_in_effect = str(effective.documents[0].get("language") or "en")
            pending = [
                option
                for option in (
                    "--models",
                    "--review-rounds",
                    "--examine-level",
                    "--documents",
                    "--hosts",
                )
                if option in unanswered
                or (option == "--examine-level" and examine_answer is None)
            ]
            for line in rigor_core.opening_lines(
                tuple(rigor_core.show_lines(effective))
            ):
                print(line)

            def remaining_from(option: str) -> int:
                return _rigor_print_refusal(
                    rigor_core.closed_terminal_refusal(
                        tuple(pending[pending.index(option) :])
                    )
                )

            def show_question(option: str) -> str:
                block, prompt = rigor_core.question(
                    option, known_hosts, language_in_effect
                )
                for line in block:
                    print(line)
                return prompt

            if "--models" in unanswered:
                prompt = show_question("--models")

                def parse_models(text: str) -> Any:
                    if text in {"", "keep"}:
                        return Success(())
                    parsed_model = rigor_core.parse_model_set(
                        text, set(published_tools)
                    )
                    if isinstance(parsed_model, Failure):
                        return parsed_model
                    return Success((parsed_model.unwrap(),))

                answers_models = ask_until_valid(prompt, parse_models)
                if answers_models is None:
                    return remaining_from("--models")

            if "--review-rounds" in unanswered:
                prompt = show_question("--review-rounds")
                current_rounds, _ = effective.review_rounds

                def parse_rounds(text: str) -> Any:
                    if text in {"", "current"}:
                        return Success("current")
                    parsed_round = rigor_core.parse_review_rounds(text, current_rounds)
                    if isinstance(parsed_round, Failure):
                        return parsed_round
                    return Success(parsed_round.unwrap())

                answers_rounds = ask_until_valid(prompt, parse_rounds)
                if answers_rounds is None:
                    return remaining_from("--review-rounds")

            if examine_answer is None:
                prompt = show_question("--examine-level")
                examine_answer = ask_until_valid(
                    prompt,
                    lambda text: rigor_core.parse_examine_level(text or "current"),
                )
                if examine_answer is None:
                    return remaining_from("--examine-level")

            if "--documents" in unanswered:
                prompt = show_question("--documents")
                answers_documents = ask_until_valid(
                    prompt,
                    lambda text: rigor_core.parse_documents(text or "keep"),
                )
                if answers_documents is None:
                    return remaining_from("--documents")
                if answers_documents == "yes" and document_language is None:
                    language_prompt = show_question("--document-language")
                    language = ask_until_valid(
                        language_prompt,
                        lambda text: Success(text or language_in_effect),
                    )
                    if language is None:
                        return _rigor_print_refusal(
                            rigor_core.closed_terminal_refusal(("--document-language",))
                        )
                    document_language = language

            if "--hosts" in unanswered:
                prompt = show_question("--hosts")
                answers_hosts = ask_until_valid(
                    prompt,
                    lambda text: rigor_core.parse_hosts_answer(text, known_hosts),
                )
                if answers_hosts is None:
                    return remaining_from("--hosts")

    answers = rigor_core.RigorAnswers(
        models=answers_models,
        review_rounds=answers_rounds,
        documents=answers_documents,
        document_language=document_language,
        hosts=answers_hosts,
        examine_level=examine_answer,
        confirmed=yes,
    )
    validated = rigor_core.validate_answers(answers, published_tools)
    if isinstance(validated, Failure):
        return _rigor_print_refusal(validated.error)

    # Resolve the host list: keep, none, or named hosts.
    if answers.hosts == "keep":
        chosen_hosts: tuple[str, ...] = ()
    elif answers.hosts == "none":
        chosen_hosts = ()
    else:
        chosen_hosts = tuple(
            host.strip() for host in (answers.hosts or "").split(",") if host.strip()
        )
    # Materialise group facts into per-role facts in the pure plan, once:
    # the store write and the host writers consume the same per-role facts.
    plan = rigor_core.write_plan(answers, published_tools)
    materialised_facts = plan["role_facts"]
    if answers.models and not materialised_facts:
        return _rigor_print_refusal(
            rigor_core.Refusal(
                "The models answer "
                + ", ".join(
                    f"{fact.target}={fact.provider}/{fact.model}"
                    for fact in answers.models
                )
                + " resolved to no published role, so nothing was written.",
                "A model fact needs a published role; the published roles are "
                "read from nWave/agents in this project and the agents home, "
                "~/.claude/agents/nw and ~/.codex/agents, and none are "
                "readable here.",
                "Publish the roles, run the command in the nWave checkout, or "
                "name single roles that exist on one of those surfaces.",
            )
        )

    # The pure host plan over the existing bytes of every chosen host's files.
    existing: dict[str, bytes] = {}
    homes: dict[str, Path] = {
        "omp": Path.home(),
        "claude-code": Path.home(),
        "codex": Path.home(),
        "copilot": Path.home(),
        "opencode": Path.home(),
        "devin": Path.home(),
    }
    for host in chosen_hosts:
        base = homes[host]
        for relative in rigor_hosts.adapter_paths(host):
            path = base / relative
            try:
                existing[relative] = path.read_bytes()
            except OSError:
                pass
        scan = rigor_hosts.adapter_scan(host)
        if scan is not None:
            directory, pattern = scan
            scan_root = base / directory
            if scan_root.is_dir():
                for path in sorted(scan_root.glob(pattern)):
                    relative = str(path.relative_to(base))
                    try:
                        existing[relative] = path.read_bytes()
                    except OSError:
                        pass
    host_resolutions: list = []
    for host_name in chosen_hosts:
        adapter = rigor_hosts.adapter_for(host_name)
        if adapter is None or adapter.apply is None:
            continue
        prefix = rigor_hosts.adapter_prefixes(adapter)
        scoped = {
            path: raw for path, raw in existing.items() if path.startswith(prefix)
        }
        try:
            host_resolutions.append(adapter.apply(scoped, materialised_facts))
        except Exception as error:  # a host fault is a refusal, never a crash
            host_resolutions.append(
                rigor_hosts.HostResolution(
                    name=host_name,
                    refusal=rigor_core.Refusal(
                        f"The {host_name} adapter failed, so nothing was "
                        "written for it.",
                        str(error),
                        "Report this to the owner; later hosts were not "
                        "attempted in this run.",
                    ),
                )
            )

    # Nothing is confirmed yet: show the summary and the disclosures.
    print("Final summary - read before you confirm")
    if answers.review_rounds is not None:
        rounds, rounds_source = effective.review_rounds
        if answers.review_rounds == "current":
            print(f"  review rounds: keep ({rounds}, {rounds_source})")
        else:
            print(
                f"  review rounds: {answers.review_rounds} "
                f"(was {rounds}, {rounds_source})"
            )
    previous_name, previous_source = effective.examine_level
    for line in rigor_core.summary_examine_lines(
        answers.examine_level, previous_name, previous_source
    ):
        print(line)
    brief_before, brief_source = effective.documents
    previous_documents = (
        f"yes, language {brief_before.get('language')}"
        if brief_before.get("enabled")
        else "no"
    )
    if answers.documents == "yes":
        print(
            f"  documents: yes, language {document_language or 'en'} "
            f"(was {previous_documents}, {brief_source})"
        )
    elif answers.documents == "no":
        print(f"  documents: no (was {previous_documents}, {brief_source})")
    else:
        print("  documents: keep (unchanged)")
    if not materialised_facts:
        print("  models: keep (unchanged)")
    for fact in materialised_facts:
        print(f"  model {fact.target}: {fact.provider}/{fact.model}")
    if answers.hosts == "keep":
        print("  hosts: keep (unchanged)")
    else:
        print(f"  hosts: {answers.hosts}")
    for resolution in host_resolutions:
        if resolution.refusal is not None:
            print("  " + resolution.refusal.render().splitlines()[0] + " (see below)")
            continue
        if resolution.files and resolution.disclosure:
            print("  " + resolution.disclosure)

    for line in rigor_core.project_file_git_lines():
        print(line)
    if not yes:
        print("Nothing is written until you answer yes.")
        confirmed_answer = ask("confirm the final summary? (yes): ")
        if confirmed_answer is None or confirmed_answer.lower() != "yes":
            return _rigor_print_refusal(
                rigor_core.Refusal(
                    "The final summary was not confirmed, so nothing was written.",
                    "Writes need the confirmation of the person.",
                    "run the command again and answer yes at the end, or pass --yes "
                    "in scripts.",
                )
            )

    from nwave_ai.platform.config_writer import ConfigMigrationError, ConfigWriter

    config_dir = _require_mutating_config_dir()
    writer = ConfigWriter(home_dir=config_dir.parent, repo_root=repo_root)

    def mutate(document: dict[str, Any]) -> None:
        rigor_core.rigor_mutate(document, plan)

    try:
        writer.update_repo(mutate)
    except ConfigMigrationError as error:
        print(
            "WHAT: the project file was not writable, so nothing was changed. "
            f"WHY: {error}. HOW: repair the unified config and retry.",
            file=sys.stderr,
        )
        return 1
    except OSError as error:
        print(
            "WHAT: the project file is not writable, so nothing was changed. "
            f"WHY: {error}. HOW: make {project_path} writable and retry.",
            file=sys.stderr,
        )
        return 1
    print(f"Written {project_path} (project).")

    # Apply the confirmed host plans: backup once, then one atomic move each.
    for resolution in host_resolutions:
        if resolution.refusal is not None:
            print(resolution.refusal.render())
            continue
        try:
            if resolution.files and resolution.disclosure:
                print("  " + resolution.disclosure)
            base = homes[resolution.name]
            for relative in resolution.backup:
                source_path = base / relative
                backup_path = base / (relative + ".nwave-bak")
                if source_path.exists() and not backup_path.exists():
                    import shutil

                    shutil.copyfile(source_path, backup_path)
            verified_adapter = rigor_hosts.adapter_for(resolution.name)
            if verified_adapter is None:
                continue
            for relative, payload in resolution.files:
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".rigor-tmp")
                with open(temporary, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.replace(target)
            if resolution.files:
                print(
                    "  "
                    + rigor_hosts.write_line(verified_adapter)
                    + f" — wrote {len(resolution.files)} file(s)."
                )
        except OSError as error:
            print(
                f"WHAT: the {resolution.name} file was not writable, so nothing "
                "was written for this host. "
                f"WHY: {error}. HOW: make the host file writable and retry.",
                file=sys.stderr,
            )
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
    print(
        "  rigor          Choose this project's quality scope (models, review rounds, documents)"
    )
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
    if action == "enable":
        try:
            home_dir = _require_mutating_config_dir().parent
        except ValueError as error:
            return _refuse_mutating_location(error)
        _declare_project_jev(
            project_root,
            home_dir,
            interactive=not assume_yes and sys.stdin.isatty(),
        )
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
    "rigor": _handle_rigor,
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
    elif command == "rigor":
        return _handle_rigor(sys.argv[2:])
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
