"""Select development launchers by their runtime, not their link spelling."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from .base import InstallationPlugin, InstallContext, PluginResult


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


class LauncherName(Enum):
    NWDES = "nwdes"
    NWAVE_AI = "nwave-ai"


@dataclass(frozen=True)
class RuntimeOrigins:
    nwave_ai: Path | None
    nwdes: Path | None


@dataclass(frozen=True)
class Matches:
    pass


@dataclass(frozen=True)
class Mismatch:
    module: str
    found: Path | None
    expected: Path


@dataclass(frozen=True)
class Unobservable:
    reason: str


RuntimeMatch = Matches | Mismatch | Unobservable


class StablePathState(Enum):
    MISSING = "missing"
    SYMLINK = "symlink"
    NOT_SYMLINK = "not-symlink"


@dataclass(frozen=True)
class AlreadyActive:
    pass


@dataclass(frozen=True)
class Activate:
    pass


@dataclass(frozen=True)
class Refuse:
    what: str
    why: str
    how: str


Plan = AlreadyActive | Activate | Refuse


@dataclass(frozen=True)
class Active:
    pass


@dataclass(frozen=True)
class Inactive:
    what: str
    why: str
    how: str


Verdict = Active | Inactive


def match_runtime(checkout: Path, origins: RuntimeOrigins) -> RuntimeMatch:
    """Compare paths normalized by the observation boundary."""
    for module, found, expected in (
        ("nwave_ai", origins.nwave_ai, checkout / "nwave_ai" / "__init__.py"),
        ("nwdes", origins.nwdes, checkout / "src" / "nwdes" / "__init__.py"),
    ):
        if found != expected:
            return Mismatch(module, found, expected)
    return Matches()


def _runtime_reason(runtime: Mismatch | Unobservable) -> str:
    match runtime:
        case Mismatch(module, found, expected):
            return f"{module} origin found {found}; expected {expected}."
        case Unobservable(reason):
            return reason


def plan_activation(
    name: LauncherName,
    current: RuntimeMatch,
    candidate: RuntimeMatch,
    stable: StablePathState,
) -> Plan:
    if isinstance(current, Matches):
        return AlreadyActive()
    if not isinstance(candidate, Matches):
        return Refuse(
            f"{name.value} launcher activation refused.",
            _runtime_reason(candidate),
            "Install this checkout editable in the installing virtual environment "
            "and rerun the development installation.",
        )
    if stable is StablePathState.NOT_SYMLINK:
        return Refuse(
            f"{name.value} launcher activation refused.",
            "The stable launcher path is not a symlink.",
            "Move that path aside and rerun the development installation.",
        )
    return Activate()


def judge(name: LauncherName, resolved: RuntimeMatch) -> Verdict:
    if isinstance(resolved, Matches):
        return Active()
    return Inactive(
        f"{name.value} PATH launcher is inactive.",
        _runtime_reason(resolved),
        "Put the launcher directory first on PATH, remove any earlier shadowing "
        "entry, and rerun the development installation using this checkout's runtime.",
    )


def report(outcomes: Iterable[Refuse | Verdict]) -> PluginResult:
    errors = [
        f"WHAT: {outcome.what}\nWHY: {outcome.why}\nHOW: {outcome.how}"
        for outcome in outcomes
        if isinstance(outcome, (Refuse, Inactive))
    ]
    return PluginResult(
        success=not errors,
        plugin_name="dev-launchers",
        message="\n".join(errors),
        errors=errors,
    )


_ORIGIN_PROBE = """import importlib.util, json
origins = {}
for name in ('nwave_ai', 'nwdes'):
    spec = importlib.util.find_spec(name)
    origins[name] = None if spec is None else spec.origin
print(json.dumps(origins))
"""


def _isolated_probe(
    environment: dict[str, str], temporary_root: str, command: Path
) -> RuntimeOrigins | None:
    try:
        with command.open(encoding="utf-8") as script:
            shebang = script.readline().rstrip()
        if not shebang.startswith("#!"):
            return None
        interpreter = shlex.split(shebang[2:])
        if not interpreter:
            return None
        with tempfile.TemporaryDirectory(
            prefix="nwave-launcher-probe-", dir=temporary_root
        ) as neutral:
            result = subprocess.run(
                [*interpreter, "-I", "-c", _ORIGIN_PROBE],
                cwd=neutral,
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        if result.returncode != 0:
            return None
        origins = json.loads(result.stdout)
        return RuntimeOrigins(
            Path(origins["nwave_ai"]) if origins["nwave_ai"] is not None else None,
            Path(origins["nwdes"]) if origins["nwdes"] is not None else None,
        )
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return None


class DevLaunchersPlugin(InstallationPlugin):
    def __init__(
        self,
        *,
        candidate_bin: Path | None = None,
        user_bin: Path | None = None,
        search_path: str | None = None,
        probe_origins: Callable[[Path], RuntimeOrigins | None] | None = None,
    ):
        super().__init__(name="dev-launchers", priority=100)
        self.candidate_bin = (
            candidate_bin if candidate_bin is not None else Path(sys.executable).parent
        ).absolute()
        self.user_bin = (
            user_bin if user_bin is not None else Path.home() / ".local" / "bin"
        ).absolute()
        self.search_path = (
            search_path if search_path is not None else os.environ.get("PATH", "")
        )
        if probe_origins is None:
            environment = dict(os.environ)
            environment.pop("PYTHONPATH", None)
            temporary_root = tempfile.gettempdir()
            self.probe_origins = lambda command: _isolated_probe(
                environment, temporary_root, command
            )
        else:
            self.probe_origins = probe_origins

    def _observe(self, checkout: Path, command: Path) -> RuntimeMatch:
        try:
            origins = self.probe_origins(command)
            if origins is None:
                return Unobservable(
                    f"Runtime origins could not be observed for {command}."
                )
            normalized = RuntimeOrigins(
                origins.nwave_ai.resolve() if origins.nwave_ai is not None else None,
                origins.nwdes.resolve() if origins.nwdes is not None else None,
            )
            return match_runtime(checkout, normalized)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            return Unobservable(f"Runtime origins for {command}: {error}")

    def _observe_path(
        self, checkout: Path, name: LauncherName
    ) -> tuple[str, RuntimeMatch]:
        try:
            command = shutil.which(name.value, path=self.search_path)
        except OSError as error:
            return "unobservable", Unobservable(str(error))
        if command is None:
            return "not found", Unobservable(f"{name.value} was not found on PATH.")
        return command, self._observe(checkout, Path(command))

    def _judge_path(self, checkout: Path, name: LauncherName) -> Verdict:
        command, runtime = self._observe_path(checkout, name)
        verdict = judge(name, runtime)
        if isinstance(verdict, Inactive):
            return replace(verdict, what=f"{verdict.what} PATH resolved to {command}.")
        return verdict

    def _activate(
        self, name: LauncherName, source: Path, stable: Path
    ) -> Refuse | None:
        try:
            self.user_bin.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix=f".{name.value}-", dir=self.user_bin
            ) as temporary:
                link = Path(temporary) / name.value
                link.symlink_to(source)
                link.replace(stable)
        except OSError as error:
            return Refuse(
                f"{name.value} launcher activation at {stable} failed.",
                str(error),
                "Fix the launcher directory's permissions or obstructing path "
                "and rerun the development installation.",
            )
        return None

    def _install_launcher(
        self, context: InstallContext, checkout: Path, name: LauncherName
    ) -> Refuse | Verdict:
        _, current = self._observe_path(checkout, name)
        source = self.candidate_bin / name.value
        stable = self.user_bin / name.value
        candidate = current
        state = StablePathState.MISSING
        if not isinstance(current, Matches):
            candidate = self._observe(checkout, source)
            if isinstance(candidate, Matches):
                try:
                    state = (
                        StablePathState.SYMLINK
                        if stat.S_ISLNK(stable.lstat().st_mode)
                        else StablePathState.NOT_SYMLINK
                    )
                except FileNotFoundError:
                    state = StablePathState.MISSING
                except OSError as error:
                    return Refuse(
                        f"{name.value} launcher activation at {stable} failed.",
                        str(error),
                        "Fix the launcher directory's permissions or obstructing path "
                        "and rerun the development installation.",
                    )
        plan = plan_activation(name, current, candidate, state)
        match plan:
            case Refuse():
                return replace(
                    plan, what=f"{plan.what} Stable path: {stable}; source: {source}."
                )
            case AlreadyActive():
                context.logger.info(f"{name.value} launcher unchanged")
                return Active()
            case Activate():
                failure = self._activate(name, source, stable)
                if failure is not None:
                    return failure
                verdict = self._judge_path(checkout, name)
                if isinstance(verdict, Active):
                    context.logger.info(f"{name.value} launcher activated")
                return verdict

    def install(self, context: InstallContext) -> PluginResult:
        try:
            checkout = context.project_root.resolve()
        except (OSError, RuntimeError) as error:
            return report(
                judge(name, Unobservable(str(error))) for name in LauncherName
            )
        return report(
            self._install_launcher(context, checkout, name) for name in LauncherName
        )

    def verify(self, context: InstallContext) -> PluginResult:
        try:
            checkout = context.project_root.resolve()
        except (OSError, RuntimeError) as error:
            return report(
                judge(name, Unobservable(str(error))) for name in LauncherName
            )
        return report(self._judge_path(checkout, name) for name in LauncherName)
