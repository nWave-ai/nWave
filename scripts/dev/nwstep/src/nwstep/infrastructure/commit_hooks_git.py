"""Effects of the commit hook check: git reads of the work tree, the hook directory and core.hooksPath, the declaring
config file, the pre-commit install, and the git clone. Every failure raises GitHooksError (GitUnavailable when git itself
cannot run) with its reason; nothing is returned as an empty fact.
"""

from __future__ import annotations

import importlib.util
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from nwstep.domain.commit_hooks import HOOK_TYPES
from nwstep.domain.delivery_root import MARKER_KEY
from nwstep.domain.source_hooks import SourceHook


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


def read_hooks(directory: Path) -> tuple[SourceHook, ...]:
    """Every regular file in directory with its permission bits and bytes; a directory that does not exist holds none."""
    if not directory.is_dir():
        return ()
    try:
        return tuple(
            SourceHook(
                name=path.name,
                mode=stat.S_IMODE(path.stat().st_mode),
                content=path.read_bytes(),
            )
            for path in sorted(directory.iterdir())
            if path.is_file()
        )
    except OSError as error:
        raise GitHooksError(
            f"the hook directory {directory} cannot be read: {error.strerror or error}"
        ) from None


def write_hooks(hooks: tuple[SourceHook, ...], directory: Path) -> None:
    """Writes each hook as a new file with its permission bits. A file already there is refused, never replaced; when a write fails, the files this call wrote are removed."""
    written: list[Path] = []
    current = directory
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for hook in hooks:
            current = directory / hook.name
            with current.open("xb") as handle:
                written.append(current)
                handle.write(hook.content)
            current.chmod(hook.mode)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        raise GitHooksError(
            f"{current} cannot be written: {error.strerror or error}"
        ) from None


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


def toplevel(root: Path) -> Path | None:
    """The resolved toplevel of the work tree holding root, or None when root is not inside one."""
    completed = _git(root, "rev-parse", "--show-toplevel")
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.decode("utf-8").strip()).resolve()


def is_linked_worktree(top: Path) -> bool:
    """True when top is a linked worktree: its git directory is not the common directory the primary checkout uses."""
    completed = _git(top, "rev-parse", "--git-dir", "--git-common-dir")
    _require(completed, f"the git directories of {top} cannot be read")
    lines = completed.stdout.decode("utf-8").splitlines()
    if len(lines) != 2:
        raise GitHooksError(
            f"the git directories of {top} cannot be read: git printed {len(lines)} lines, expected 2"
        )
    git_dir, common_dir = ((top / line).resolve() for line in lines)
    return git_dir != common_dir


def clone_marker(top: Path) -> str | None:
    """The delivery marker the clone command wrote in top, or None when none was written."""
    completed = _git(top, "config", "--local", "--get", MARKER_KEY)
    if completed.returncode == 1:
        return None
    _require(completed, f"the delivery marker of {top} cannot be read")
    return completed.stdout.decode("utf-8").strip()


def mark_clone(root: Path) -> None:
    """Writes the delivery marker, the toplevel path, into the local config of the work tree holding root."""
    top = toplevel(root)
    if top is None:
        raise GitHooksError(f"{root} is not inside a git work tree")
    completed = _git(top, "config", "--local", MARKER_KEY, str(top))
    _require(completed, f"the delivery marker of {top} cannot be written")


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
