"""Write the stable nwstep launcher for development installs.

nwstep ships no Python distribution (no pyproject or setup under
``scripts/dev/nwstep``), so pip creates no console script for the
runtime-origin probe to observe and ``DevLaunchersPlugin`` cannot carry
it. This plugin renders a small Python launcher over THIS checkout and
writes it idempotently into the stable user bin instead. A non-dev
install never creates it: creation is dev-gated inside the plugin, and
a non-dev install instead removes a launcher a previous dev install
wrote, so a dev-to-non-dev downgrade leaves no dangling private entry
point.

The plugin's priority (99) puts it before DevLaunchersPlugin (100): the
registry stops at the first failing plugin, and the dev-launchers
verdict is an environment observation (another checkout's runtime on
PATH) that must not suppress the independent nwstep launcher write. The
traded case - a nwstep refusal stopping the dev launchers - only arises
when the checkout lacks scripts/dev/nwstep or the bin directory is
unwritable, where the dev launchers fail anyway.
"""

from __future__ import annotations

import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .base import InstallationPlugin, InstallContext, PluginResult


LAUNCHER_NAME = "nwstep"
_TOOL_SRC = Path("scripts") / "dev" / "nwstep" / "src"
_TOOL_PACKAGE = _TOOL_SRC / "nwstep" / "__init__.py"


@dataclass(frozen=True)
class LauncherPlan:
    """What the launcher must contain; pure data, no I/O."""

    interpreter: str
    src_root: Path


def render_launcher(plan: LauncherPlan) -> str:
    """The launcher text: run THIS checkout nwstep from any project."""
    return (
        f"#!{plan.interpreter}\n"
        '"""Stable nwstep launcher written by the nWave development install."""\n'
        "import sys\n"
        "\n"
        f"sys.path.insert(0, {str(plan.src_root)!r})\n"
        "from nwstep.infrastructure.cli import Cli\n"
        "\n"
        "sys.exit(Cli().run(sys.argv[1:]))\n"
    )


def is_nwave_launcher_text(text: str) -> bool:
    """True when the text is a launcher this installer family renders.

    The uninstall may run after the checkout is gone, so ownership is the
    renderer's signature - a shebang, the sys.path insert of a checkout's
    scripts/dev/nwstep/src and the Cli import - not an exact render.
    """
    return (
        text.startswith("#!")
        and "scripts/dev/nwstep/src" in text
        and "from nwstep.infrastructure.cli import Cli" in text
    )


def _refusal(what: str, why: str, how: str) -> PluginResult:
    message = f"WHAT: {what}\nWHY: {why}\nHOW: {how}"
    return PluginResult(False, "nwstep-launcher", message, errors=[message])


class NwstepLauncherPlugin(InstallationPlugin):
    """Dev-only: keep the stable nwstep launcher pointing at this checkout."""

    def __init__(self, *, user_bin: Path | None = None):
        super().__init__(name="nwstep-launcher", priority=99)
        self.user_bin = (
            user_bin if user_bin is not None else Path.home() / ".local" / "bin"
        ).absolute()

    def stable_path(self) -> Path:
        return self.user_bin / LAUNCHER_NAME

    def install(self, context: InstallContext) -> PluginResult:
        if context.dry_run:
            return PluginResult(
                True,
                self.name,
                "nwstep launcher: nothing written on a dry run",
            )
        if not context.dev_mode:
            return self._non_dev(context)
        checkout = context.project_root
        if checkout is None:
            return _refusal(
                "nwstep launcher creation without a project root.",
                "The launcher must point at the checkout hosting the tool.",
                "Run the development installation from that checkout.",
            )
        src_root = checkout / _TOOL_SRC
        if not (checkout / _TOOL_PACKAGE).is_file():
            return _refusal(
                f"nwstep source tree not found at {src_root}.",
                "The launcher would point at a tool this checkout does not carry.",
                "Run the development installation from the checkout hosting "
                "scripts/dev/nwstep.",
            )
        failure = self._write(LauncherPlan(sys.executable, src_root))
        if failure is not None:
            return failure
        context.logger.info(f"nwstep launcher written to {self.stable_path()}")
        return PluginResult(
            True,
            self.name,
            f"nwstep launcher active at {self.stable_path()}",
            installed_files=[self.stable_path()],
        )

    def verify(self, context: InstallContext) -> PluginResult:
        stable = self.stable_path()
        if not context.dev_mode:
            # A non-dev install owns no launcher: absent is healthy, and a
            # file this install deliberately left (not the exact render of
            # its checkout) is not this install's to judge.
            try:
                stable.read_text(encoding="utf-8")
                message = (
                    f"{stable} is not a non-dev surface; owned by a "
                    "development install, not judged by this install"
                )
            except OSError:
                message = "No nwstep launcher; healthy for a non-dev install"
            return PluginResult(True, self.name, message)
        checkout = context.project_root
        stable = self.stable_path()
        if checkout is None or not (checkout / _TOOL_PACKAGE).is_file():
            return _refusal(
                f"nwstep launcher verification needs the tool at "
                f"{checkout / _TOOL_SRC if checkout else _TOOL_SRC}.",
                "Nothing anchors the stable launcher to this checkout.",
                "Run the development installation from the checkout hosting "
                "scripts/dev/nwstep.",
            )
        expected = render_launcher(LauncherPlan(sys.executable, checkout / _TOOL_SRC))
        try:
            actual = stable.read_text(encoding="utf-8")
            executable = bool(stat.S_IMODE(stable.stat().st_mode) & stat.S_IXUSR)
        except OSError as error:
            return _refusal(
                f"nwstep launcher missing at {stable}.",
                str(error),
                "Rerun the development installation.",
            )
        if actual != expected or not executable:
            return _refusal(
                f"nwstep launcher at {stable} is not this checkout's launcher.",
                "The stable launcher is stale, was written by another or a "
                "nested checkout, or was modified after the install.",
                "Rerun the development installation to rewrite it.",
            )
        return PluginResult(True, self.name, f"nwstep launcher verified at {stable}")

    def _non_dev(self, context: InstallContext) -> PluginResult:
        """Refuse creation outside a dev install and remove a launcher this
        installer wrote, so a dev-to-non-dev downgrade leaves no dangling
        private entry point (review N4). A file that is not the launcher
        this installer renders is foreign and left untouched."""
        checkout = context.project_root
        stable = self.stable_path()
        owned = False
        if checkout is not None and (checkout / _TOOL_PACKAGE).is_file():
            expected = render_launcher(
                LauncherPlan(sys.executable, checkout / _TOOL_SRC)
            )
            try:
                owned = stable.read_text(encoding="utf-8") == expected
            except OSError:
                owned = False
        if owned:
            try:
                stable.unlink()
            except OSError as error:
                return _refusal(
                    f"the dev-only nwstep launcher at {stable} could not be removed.",
                    str(error),
                    "Remove it by hand and rerun the install.",
                )
            return PluginResult(
                True,
                self.name,
                f"Removed the dev-only nwstep launcher it owned at {stable}",
            )
        if stable.exists():
            return PluginResult(
                True,
                self.name,
                f"{stable} is not the launcher this installer renders; left untouched",
            )
        return PluginResult(
            True,
            self.name,
            "No nwstep launcher in this home; nothing to do outside a dev install",
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove the stable nwstep launcher when nWave wrote it; a foreign
        file at that path is left untouched."""
        stable = self.stable_path()
        try:
            text = stable.read_text(encoding="utf-8")
        except OSError:
            return PluginResult(
                True,
                self.name,
                f"No nwstep launcher at {stable}; nothing to remove",
            )
        if not is_nwave_launcher_text(text):
            return PluginResult(
                True,
                self.name,
                f"{stable} is not an nWave nwstep launcher; left untouched",
            )
        try:
            stable.unlink()
        except OSError as error:
            return _refusal(
                f"the nWave nwstep launcher at {stable} could not be removed.",
                str(error),
                "Remove it by hand.",
            )
        return PluginResult(
            True,
            self.name,
            f"Removed the nWave nwstep launcher at {stable}",
        )

    def _write(self, plan: LauncherPlan) -> PluginResult | None:
        try:
            self.user_bin.mkdir(parents=True, exist_ok=True)
            text = render_launcher(plan)
            with tempfile.TemporaryDirectory(
                prefix=".nwstep-launcher-", dir=self.user_bin
            ) as temporary:
                candidate = Path(temporary) / LAUNCHER_NAME
                candidate.write_text(text, encoding="utf-8")
                candidate.chmod(0o755)
                candidate.replace(self.stable_path())
        except OSError as error:
            return _refusal(
                f"nwstep launcher write at {self.stable_path()} failed.",
                str(error),
                "Fix the launcher directory permissions and rerun the "
                "development installation.",
            )
        return None
