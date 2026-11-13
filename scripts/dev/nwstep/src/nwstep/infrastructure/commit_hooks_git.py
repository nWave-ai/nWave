"""Effects of the commit hook check: git reads of the work tree, the hook directory and core.hooksPath, the declaring
config file, the pre-commit install, and the git clone. Every failure raises GitHooksError (GitUnavailable when git itself
cannot run) with its reason; nothing is returned as an empty fact.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from nwstep.domain.commit_hooks import HOOK_TYPES


if TYPE_CHECKING:
    from pathlib import Path


TIMEOUT_S = 300
CONFIG_NAME = ".pre-commit-config.yaml"
INSTALL_ARGUMENTS = tuple(argument for hook in HOOK_TYPES for argument in ("-t", hook))


class GitHooksError(Exception):
    """A git or pre-commit effect could not run or failed; the message is the reason."""


class GitUnavailable(GitHooksError):
    """The git executable cannot be started at all."""


def inside_work_tree(root: Path) -> bool:
    completed = _git(root, "rev-parse", "--is-inside-work-tree")
    return completed.returncode == 0 and completed.stdout.strip() == b"true"


def declares_hooks(root: Path) -> bool:
    return (root / CONFIG_NAME).is_file()


def hooks_directory(root: Path) -> Path:
    completed = _git(root, "rev-parse", "--git-path", "hooks")
    _require(completed, f"the hook directory of {root} cannot be read")
    return (root / completed.stdout.decode("utf-8").strip()).resolve()


def hooks_path_value(root: Path) -> str | None:
    completed = _git(root, "config", "--get", "core.hooksPath")
    if completed.returncode == 1:
        return None
    _require(completed, f"core.hooksPath of {root} cannot be read")
    return completed.stdout.decode("utf-8").strip()


def hook_file_contents(root: Path) -> tuple[bytes | None, ...]:
    directory = hooks_directory(root)
    return tuple(_read_or_none(directory / name) for name in HOOK_TYPES)


def installer_available() -> bool:
    return importlib.util.find_spec("pre_commit") is not None


def install_hooks(root: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "pre_commit", "install", *INSTALL_ARGUMENTS],
        cwd=root,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=TIMEOUT_S,
        check=False,
    )
    return completed.returncode == 0, (completed.stdout + completed.stderr).strip()


def clone(source: str, destination: Path) -> None:
    try:
        completed = subprocess.run(
            ["git", "clone", "--quiet", source, str(destination)],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_S,
            check=False,
        )
    except OSError as error:
        raise GitUnavailable(f"git cannot be run: {error.strerror or error}") from None
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitHooksError(detail or "git clone exited without a message")


def remove_tree(path: Path) -> None:
    shutil.rmtree(path)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_S,
            check=False,
        )
    except OSError as error:
        raise GitUnavailable(f"git cannot be run: {error.strerror or error}") from None


def _require(completed: subprocess.CompletedProcess[bytes], reason: str) -> None:
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitHooksError(f"{reason}: {detail or 'git exited without a message'}")


def _read_or_none(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes()
