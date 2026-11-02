"""Owner-bound application service for the mutating public update journey."""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Literal


if TYPE_CHECKING:
    from packaging.version import Version

from nwave_ai.platform.package_manager import (
    PMBackend,
    detect_running_interpreter_owner,
)


StageProgress = Callable[[str, Literal["started", "completed"]], None]


UpdateState = Literal["succeeded", "up-to-date", "refused"]


@dataclass(frozen=True)
class UpdateResult:
    """Immutable public outcome of one update application attempt."""

    state: UpdateState
    version: Version | None
    completed_stages: tuple[str, ...] = ()
    failed_stage: str | None = None
    command: tuple[str, ...] = ()
    cause: str = ""
    recovery: str = ""
    termination_unknown: bool = False


class UpdateService:
    """Run replacement, proof, synchronization, and migration fail-closed."""

    def __init__(self, interpreter: Path | None = None) -> None:
        self._interpreter = interpreter or Path(sys.executable)

    def apply(
        self,
        *,
        current_version: Version,
        discovered_version: Version,
        root: Path,
        on_stage: StageProgress | None = None,
        before_replacement: Callable[[str], UpdateResult | None] | None = None,
    ) -> UpdateResult:
        """Apply a newer release only when its running-install owner is known.

        ``before_replacement`` receives the selected platform after every
        read-only preflight and before the first mutating stage; a returned
        refusal stops the update with no package or host change.
        """
        pending = self.pending_update(self._interpreter)
        if pending is not None:
            return pending
        if (
            current_version.is_prerelease
            or current_version.is_devrelease
            or current_version.local
        ):
            return self._refusal(
                "release-channel",
                (),
                "the installed beta, dev, or local version has no supported stable update path",
                recovery="keep the selected channel and use its documented source or release install route",
            )
        origin = self.release_origin()
        if origin is not None:
            return origin
        if sys.platform == "win32":
            return self._refusal(
                "platform-process-tree",
                (),
                "automatic Windows installation cannot yet stop and reap installer descendants reliably",
                recovery=(
                    "use `nwave-ai update --check` for release information, then perform "
                    "a supervised explicit package update and selected-host install only "
                    "after work is complete; no update stage started"
                ),
            )
        if discovered_version <= current_version:
            selection = self._selected_platform()
            if isinstance(selection, UpdateResult):
                return selection
            return UpdateResult(state="up-to-date", version=discovered_version)

        owner = detect_running_interpreter_owner(self._interpreter)
        if owner == "unknown":
            return self._refusal(
                "package-owner",
                (str(self._interpreter),),
                (
                    "the package owner of the running interpreter is unknown; "
                    "choosing an installer from PATH is unsafe"
                ),
                recovery=(
                    "verify the named interpreter's installed package metadata and owner, "
                    "then use that verified package manager explicitly; no package or host sync started"
                ),
            )

        selection = self._selected_platform()
        if isinstance(selection, UpdateResult):
            return selection
        platform, selected_environment = selection

        console = self._interpreter.with_name("nwave-ai")
        proof_command = (str(console), "--version")
        replacement = self._replacement_command(owner, discovered_version)
        if not console.is_file() or not os.access(console, os.X_OK):
            return self._refusal(
                "verify-executable",
                proof_command,
                "the owned nwave-ai console sibling is missing or is not executable",
                recovery=(
                    f"restore the owned console with the verified package manager "
                    f"using `{shlex.join(replacement)}`, then check `{shlex.join(proof_command)}`; "
                    "no package replacement or framework sync started"
                ),
            )

        if before_replacement is None:
            from nwave_ai.update.activity import ReplacementLease

            lease = ReplacementLease(None, interpreter=self._interpreter)
            try:
                return self.apply(
                    current_version=current_version,
                    discovered_version=discovered_version,
                    root=root,
                    on_stage=on_stage,
                    before_replacement=lease.before_replacement,
                )
            finally:
                lease.close()
        refusal = before_replacement(platform)
        if refusal is not None:
            return refusal
        # Recheck after acquiring the lease: another updater may have failed
        # between the first observation and lock acquisition.
        pending = self.pending_update(self._interpreter)
        if pending is not None:
            return pending
        document: dict[str, object] = {
            "schema-version": 1,
            "target_version": str(discovered_version),
            "platform": platform,
            "environment": selected_environment,
            "root": str(root.resolve()),
            "interpreter": str(self._interpreter.absolute()),
            "owner": owner,
            "completed_stages": [],
            "running_stage": "replace-package",
        }
        return self._finish_update(
            document,
            discovered_version,
            replace_package=True,
            on_stage=on_stage,
        )

    @staticmethod
    def _recovery_command(document: dict[str, object]) -> str:
        interpreter = document.get("interpreter")
        console = (
            Path(interpreter).with_name("nwave-ai")
            if isinstance(interpreter, str)
            else Path(sys.executable).with_name("nwave-ai")
        )
        environment = document.get("environment")
        prefix = (
            ["env", *(f"{key}={value}" for key, value in environment.items())]
            if isinstance(environment, dict)
            else []
        )
        return shlex.join(
            [
                *prefix,
                str(console),
                "update",
                "--recover",
                "--yes",
                "--confirm-stopped",
            ]
        )

    @classmethod
    def pending_update(cls, interpreter: Path | None = None) -> UpdateResult | None:
        """Refuse checks and ordinary updates while interruption evidence remains."""
        from nwave_ai.platform.session_registry import (
            SessionActivityRegistry,
        )
        from nwave_ai.update.package_activity import PackageActivityLease

        registry = SessionActivityRegistry.selected()
        if registry is None:
            return cls._refusal(
                "update-recovery",
                (),
                "the selected activity registry cannot be located",
                recovery="repair invalid absolute host path overrides before checking update state",
            )
        package = PackageActivityLease.for_interpreter(interpreter)
        journal = registry
        if package is not None and package.registry.update_in_progress() is not None:
            journal = package.registry
        document = journal.update_in_progress()
        if document is None:
            return None
        return cls._refusal(
            "update-incomplete",
            (),
            f"unresolved update at {journal.in_progress_path}: target "
            f"{document.get('target_version', 'unknown')}, completed stages "
            f"{document.get('completed_stages', [])}, interrupted stage "
            f"{document.get('running_stage', 'unknown')}; "
            f"{document.get('problem', 'package/framework consistency is not verified')}",
            recovery=(
                "close host sessions and establish that the previous updater and all "
                "installer descendants have stopped, repair the named cause, then run "
                f"`{cls._recovery_command(document)}`; recovery verifies the pinned package, "
                "replays selected-host dry-run/synchronization and artifact migration under "
                "the update lock, and only then removes this marker; do not delete it"
            ),
        )

    def recover(
        self,
        *,
        on_stage: StageProgress | None = None,
    ) -> UpdateResult:
        """Repair an interrupted update without replacing the package implicitly."""
        from packaging.version import InvalidVersion, Version

        from nwave_ai.platform.session_registry import (
            SessionActivityRegistry,
        )
        from nwave_ai.update.activity import ReplacementLease
        from nwave_ai.update.package_activity import PackageActivityLease

        registry = SessionActivityRegistry.selected()
        if registry is None:
            return self._refusal(
                "update-recovery", (), "selected activity registry is invalid"
            )
        selection = self._selected_platform()
        if isinstance(selection, UpdateResult):
            return selection
        platform, environment = selection
        lease = ReplacementLease(None, interpreter=self._interpreter)
        try:
            refusal = lease.before_replacement(platform)
            if refusal is not None:
                return refusal
            package = PackageActivityLease.for_interpreter(self._interpreter)
            local_document = registry.update_in_progress()
            package_document = (
                package.registry.update_in_progress() if package is not None else None
            )
            document = (
                package_document if package_document is not None else local_document
            )
            if document is None:
                return self._refusal(
                    "update-recovery",
                    (),
                    "there is no interrupted update to recover",
                    recovery="use `nwave-ai update --check` to inspect release availability",
                )
            try:
                target = Version(str(document["target_version"]))
                root = Path(str(document["root"]))
                valid = (
                    document.get("schema-version") == 1
                    and document.get("platform") == platform
                    and document.get("environment") == environment
                    and (
                        local_document is None
                        or package_document is None
                        or all(
                            local_document.get(key) == package_document.get(key)
                            for key in (
                                "schema-version",
                                "target_version",
                                "platform",
                                "environment",
                                "root",
                                "interpreter",
                                "owner",
                            )
                        )
                    )
                    and document.get("interpreter") == str(self._interpreter.absolute())
                    and document.get("owner") in ("uv", "pipx", "pip")
                    and document.get("owner")
                    == detect_running_interpreter_owner(self._interpreter)
                    and root.is_absolute()
                    and root.is_dir()
                    and isinstance(document.get("completed_stages"), list)
                    and all(
                        isinstance(stage, str) for stage in document["completed_stages"]
                    )
                    and not (
                        target.is_prerelease or target.is_devrelease or target.local
                    )
                )
            except (KeyError, InvalidVersion, OSError, ValueError):
                valid = False
            if not valid:
                return self._refusal(
                    "update-recovery",
                    (),
                    f"the marker {registry.in_progress_path} does not match the owned installation, "
                    "selected paths, stable target, or an existing absolute project root",
                    recovery=(
                        f"use the recorded selection via `{self._recovery_command(document)}`; "
                        "restore the recorded interpreter and project root. If the marker is "
                        "damaged, restore its original contents from backup; no reset/clearance "
                        "is safe without the original update identity"
                    ),
                )
            return self._finish_update(
                document,
                target,
                replace_package=False,
                on_stage=on_stage,
            )
        finally:
            lease.close()

    def _finish_update(
        self,
        document: dict[str, object],
        target: Version,
        *,
        replace_package: bool,
        on_stage: StageProgress | None,
    ) -> UpdateResult:
        from nwave_ai.platform.session_registry import (
            SessionActivityRegistry,
        )
        from nwave_ai.update.package_activity import PackageActivityLease

        registry = SessionActivityRegistry.selected()
        assert registry is not None  # selected paths were established before the lease
        package = PackageActivityLease.for_interpreter(self._interpreter)
        journals = [package.registry, registry] if package is not None else [registry]
        root = Path(str(document["root"]))
        platform = str(document["platform"])
        environment = document["environment"]
        assert isinstance(environment, dict)
        console = self._interpreter.with_name("nwave-ai")
        owner = document["owner"]
        assert owner in ("uv", "pipx", "pip")
        replacement = self._replacement_command(owner, target)
        explicit_install = shlex.join(
            (
                "env",
                *(f"{key}={value}" for key, value in environment.items()),
                str(console),
                "install",
                "--yes",
                "--no-project-guidance",
                "--platform",
                platform,
            )
        )
        recovery = (
            "close host sessions and verify the updater and installer descendants have stopped; "
            f"repair the named cause, then run `{self._recovery_command(document)}`. "
            f"If the owned package/console is absent or is not {target}, first restore it "
            f"explicitly with `{shlex.join(replacement)}`. Recovery must verify the package, "
            f"run selected-host synchronization `{explicit_install}` and artifact migration "
            f"`{shlex.join((str(console), 'migrate-artifacts', '--apply', '--root', str(root)))}` "
            "before marker clearance"
        )
        stages = [
            ("verify-executable", (str(console), "--version")),
            (
                "preflight-framework",
                (
                    str(console),
                    "install",
                    "--dry-run",
                    "--yes",
                    "--no-project-guidance",
                    "--platform",
                    platform,
                ),
            ),
            (
                "synchronize-framework",
                (
                    str(console),
                    "install",
                    "--yes",
                    "--no-project-guidance",
                    "--platform",
                    platform,
                ),
            ),
            (
                "migrate-artifacts",
                (str(console), "migrate-artifacts", "--apply", "--root", str(root)),
            ),
        ]
        if replace_package:
            stages.insert(0, ("replace-package", replacement))
        completed = tuple(document["completed_stages"])
        try:
            for stage, command in stages:
                document["running_stage"] = stage
                for journal in journals:
                    journal.record_update(document)
                if stage == "migrate-artifacts" and (
                    not console.is_file() or not os.access(console, os.X_OK)
                ):
                    return self._refusal(
                        stage,
                        command,
                        "the owned nwave-ai console sibling is missing or is not executable",
                        completed=completed,
                        recovery=recovery,
                    )
                if on_stage:
                    on_stage(stage, "started")
                result = self._run_stage(
                    stage,
                    command,
                    cwd=root,
                    expected_version=target if stage == "verify-executable" else None,
                    environment=environment if stage != "replace-package" else None,
                )
                if result is not None:
                    return replace(
                        result, completed_stages=completed, recovery=recovery
                    )
                if stage not in completed:
                    completed += (stage,)
                document["completed_stages"] = list(completed)
                document["running_stage"] = None
                for journal in journals:
                    journal.record_update(document)
                if on_stage:
                    on_stage(stage, "completed")
            # Keep the shared marker until local clearance finishes. If killed
            # between these removals, recovery replays from the shared journal.
            for journal in reversed(journals):
                journal.clear_completed_update()
        except OSError as exc:
            return self._refusal(
                "update-journal",
                (),
                f"update evidence/output could not be persisted: {exc}",
                completed=completed,
                recovery=recovery,
            )
        return UpdateResult(
            state="succeeded", version=target, completed_stages=completed
        )

    @staticmethod
    def release_origin() -> UpdateResult | None:
        try:
            distribution = metadata.distribution("nwave-ai")
            direct_url = distribution.read_text("direct_url.json")
        except (metadata.PackageNotFoundError, OSError) as exc:
            return UpdateService._refusal(
                "release-origin",
                (),
                f"the installed nwave-ai package origin cannot be established: {exc}",
                recovery=(
                    "inspect the owned nwave-ai distribution metadata and restore its "
                    "selected source with the verified package manager before retrying"
                ),
            )
        if direct_url is None:
            return None
        try:
            origin = json.loads(direct_url)
        except json.JSONDecodeError:
            origin = None
        reason = (
            "the installed nwave-ai direct_url.json is malformed"
            if not isinstance(origin, dict) or not isinstance(origin.get("url"), str)
            else "the installed nwave-ai package records an explicit non-index source"
        )
        return UpdateService._refusal(
            "release-origin",
            (),
            reason,
            recovery=(
                "inspect the installed nwave-ai.dist-info/direct_url.json and update or "
                "reinstall from its recorded source with the verified package manager; "
                "a PyPI stable replacement would change the selected channel"
            ),
        )

    @staticmethod
    def _selected_platform() -> tuple[str, dict[str, str]] | UpdateResult:
        from nwave_ai.platform.locations import NWaveLocations
        from nwave_ai.platform.result import Failure

        located = NWaveLocations.resolve(
            home=Path.home(),
            repo_root=Path.cwd(),
            agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
            claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
            codex_config_override=os.environ.get("CODEX_HOME"),
        )
        if isinstance(located, Failure):
            return UpdateService._refusal(
                "install-provenance",
                (),
                f"selected install destination is invalid: {located.error}",
                recovery="set absolute host destinations or unset invalid overrides, then retry",
            )
        path = located.unwrap().agents_home / ".nwave" / "config.json"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return UpdateService._refusal(
                "install-provenance",
                (),
                f"global install configuration cannot be read: {exc}",
                recovery="rerun the selected host install to record its target and mode",
            )
        install = document.get("install") if isinstance(document, dict) else None
        if not isinstance(install, dict):
            return UpdateService._refusal(
                "install-provenance",
                (),
                "install target and mode are absent",
                recovery="rerun the selected host install to record its target and mode",
            )
        targets = install.get("target_platforms")
        dev_mode = install.get("dev_mode")
        if (
            not isinstance(targets, list)
            or not isinstance(dev_mode, bool)
            or any(not isinstance(target, str) for target in targets)
        ):
            return UpdateService._refusal(
                "install-provenance",
                (),
                "persisted host targets or dev mode are invalid",
                recovery="rerun the selected host install to repair its target and mode",
            )
        names = {
            "claude_code": "claude-code",
            "codex": "codex",
            "opencode": "opencode",
            "copilot": "copilot",
        }
        host_paths = install.get("host_paths")
        keys = {
            "agents_home": "NWAVE_AGENTS_HOME",
            "claude_config_dir": "CLAUDE_CONFIG_DIR",
            "codex_config_dir": "CODEX_HOME",
        }
        if not isinstance(host_paths, dict) or any(
            not isinstance(host_paths.get(key), str)
            or not Path(host_paths[key]).is_absolute()
            for key in keys
        ):
            return UpdateService._refusal(
                "install-provenance",
                (),
                "persisted host destinations are absent or invalid",
                recovery="rerun the selected host install to record its destinations",
            )
        locations = located.unwrap()
        if Path(host_paths["agents_home"]).resolve() != locations.agents_home.resolve():
            return UpdateService._refusal(
                "install-provenance",
                (),
                "recorded agents_home does not match the active activity registry",
                recovery=(
                    "select the recorded NWAVE_AGENTS_HOME or explicitly reinstall "
                    "to record the intended agents home; no package replacement started"
                ),
            )
        environment = {env_name: host_paths[key] for key, env_name in keys.items()}
        selected = set(targets)
        if len(targets) == 1 and targets[0] in names:
            platform = names[targets[0]]
        elif len(targets) == len(names) and selected == set(names):
            platform = "all"
        else:
            return UpdateService._refusal(
                "install-provenance",
                (),
                "the selected host combination cannot be replayed by the installer",
                recovery="rerun install for one explicit --platform host or --platform all before updating",
            )
        if dev_mode:
            return UpdateService._refusal(
                "selected-mode",
                (),
                "a public stable package cannot prove it contains the selected --dev assets",
                recovery=(
                    "update the source checkout, then run "
                    f"`nwave-ai install --dev --platform {platform}` from that checkout"
                ),
            )
        return platform, environment

    def _replacement_command(
        self, owner: PMBackend, version: Version
    ) -> tuple[str, ...]:
        package = f"nwave-ai=={version}"
        if owner == "uv":
            return ("uv", "tool", "install", "--reinstall", package)
        if owner == "pipx":
            return ("pipx", "install", "--force", package)
        # ``pip`` ownership can only originate from the detector's explicit
        # override; executing through the owned interpreter preserves that bind.
        return (str(self._interpreter), "-m", "pip", "install", "--upgrade", package)

    def _run_stage(
        self,
        stage: str,
        command: tuple[str, ...],
        *,
        expected_version: Version | None = None,
        environment: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> UpdateResult | None:
        from nwave_ai.platform.update_timing import UPDATE_TIMING
        from nwave_ai.update.process_control import stop_process

        process: subprocess.Popen[str] | None = None
        previous_handlers = {}
        interrupted = False

        def cancel_stage(_signum: int, _frame: object) -> None:
            nonlocal interrupted
            if interrupted:
                return
            interrupted = True
            # During Popen, defer cancellation until the child handle is owned.
            if process is not None:
                raise InterruptedError("update interrupted")

        try:
            if os.name != "nt":
                for signum in (signal.SIGTERM, signal.SIGINT):
                    previous_handlers[signum] = signal.signal(signum, cancel_stage)

            process = subprocess.Popen(
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(cwd) if cwd else None,
                start_new_session=os.name != "nt",
                env={**os.environ, **environment} if environment else None,
            )
            if interrupted:
                raise InterruptedError("update interrupted during process launch")
            stdout, stderr = process.communicate(timeout=UPDATE_TIMING.stage_seconds)
        except (subprocess.TimeoutExpired, InterruptedError, KeyboardInterrupt) as exc:
            # A second termination signal must not interrupt bounded cleanup.
            for signum in previous_handlers:
                signal.signal(signum, signal.SIG_IGN)
            problem = stop_process(process) if process is not None else ""
            partial = (
                (exc.stderr or exc.stdout or b"")
                if isinstance(exc, subprocess.TimeoutExpired)
                else ""
            )
            if isinstance(partial, bytes):
                partial = partial.decode(errors="replace")
            cause = (
                "timed out"
                if isinstance(exc, subprocess.TimeoutExpired)
                else "interrupted"
            )
            cause += "; package or host state is unknown"
            if partial.strip():
                cause += f": {partial.strip()}"
            if problem:
                cause += f"; process-tree termination is unknown: {problem}"
            return replace(
                self._refusal(stage, command, cause),
                termination_unknown=bool(problem),
            )
        except OSError as exc:
            for signum in previous_handlers:
                signal.signal(signum, signal.SIG_IGN)
            problem = stop_process(process) if process is not None else ""
            cause = str(exc)
            if problem:
                cause += f"; process-tree termination is unknown: {problem}"
            return replace(
                self._refusal(stage, command, cause),
                termination_unknown=bool(problem),
            )
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)

        if process.returncode != 0:
            output = (stderr or stdout or "").strip()
            cause = f"exit {process.returncode}"
            if output:
                cause = f"{cause}: {output}"
            return self._refusal(stage, command, cause)

        if expected_version is not None:
            observed = (stdout or "").strip()
            expected = f"nwave-ai {expected_version}"
            if observed != expected:
                return self._refusal(
                    stage,
                    command,
                    f"expected {expected!r}, observed {observed!r}",
                )
        return None

    @staticmethod
    def _refusal(
        stage: str,
        command: tuple[str, ...],
        cause: str,
        *,
        completed: tuple[str, ...] = (),
        recovery: str = "",
    ) -> UpdateResult:
        if not recovery:
            recovery = {
                "replace-package": "inspect the package-manager state before retrying explicitly; package replacement may be incomplete and framework sync did not start",
                "verify-executable": "inspect the owned nwave-ai executable and its version before retrying; package replacement completed, framework sync did not start",
                "preflight-framework": "repair the named dry-run refusal for the selected host, then retry explicitly; package replacement completed, framework sync did not start",
                "synchronize-framework": "inspect the selected host installation and its backup, then rerun the same explicit host install after repair; package replacement completed",
                "migrate-artifacts": "run the owned nwave-ai migrate-artifacts --dry-run for the named root, repair the reported artifact path, then retry --apply explicitly; package and framework sync completed",
            }.get(stage, "inspect the named stage and retry explicitly")
        return UpdateResult(
            state="refused",
            version=None,
            failed_stage=stage,
            command=command,
            cause=cause,
            completed_stages=completed,
            recovery=recovery,
        )
