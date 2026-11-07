"""Shared utilities for attribution config read/write and hook lifecycle.

Used by AttributionPlugin (install-time) and CLI (post-install toggle).
The hook script does NOT import this module -- it reads JSON directly.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from scripts.shared.git_hooks_paths import resolve_hooks_dir
from scripts.shared.hook_shim import FALLBACK_MARKER, ORIGINAL_SUFFIX
from scripts.shared.install_paths import resolve_python_path_for_shell


_SHELL_UNSAFE = re.compile(r"[;&|`(){}]")


_DEFAULT_TRAILER = "Co-Authored-By: nWave <nwave@nwave.ai>"
_HOOK_SCRIPT_NAME = "nwave_attribution_hook.py"
_HOOK_SHIM_NAME = "prepare-commit-msg"


def read_global_config(config_dir: Path) -> dict:
    """Read config.json, returning empty dict on error."""
    config_file = config_dir / "config.json"
    try:
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def write_global_config(config_dir: Path, config: dict) -> None:
    """Replace config_dir/config.json through the sole atomic configuration writer."""
    from nwave_ai.platform.config_writer import ConfigWriter

    # update_global touches only the global tier, so the repository tier is
    # never written here; config_dir stands in for the required repo_root.
    writer = ConfigWriter(global_dir=config_dir, repo_root=config_dir)

    def replace(document: dict) -> None:
        document.clear()
        document.update(config)

    writer.update_global(replace)


@dataclass(frozen=True)
class UnreadableAttributionPreference:
    """A stored preference that cannot be used or replaced by a default."""

    path: Path
    reason: str

    def warning(self) -> str:
        return (
            f"Attribution preference in {self.path} is unreadable: {self.reason}. "
            "Attribution is absent for this run; the saved value is left untouched. "
            "Restore a readable config file, then run `nwave-ai attribution on` "
            "or `nwave-ai attribution off` to choose a valid preference."
        )


def classify_attribution_preference(
    config: object, path: Path
) -> bool | UnreadableAttributionPreference | None:
    """Interpret stored data without effects; only a boolean is a saved choice."""
    if not isinstance(config, dict):
        return UnreadableAttributionPreference(path, "config must be a JSON object")
    if "attribution" not in config:
        return None
    attribution = config["attribution"]
    if not isinstance(attribution, dict):
        return UnreadableAttributionPreference(
            path, "attribution must be an object containing a boolean enabled value"
        )
    enabled = attribution.get("enabled")
    if not isinstance(enabled, bool):
        return UnreadableAttributionPreference(
            path, "attribution.enabled must be a boolean"
        )
    return enabled


def read_attribution_preference(
    config_dir: Path,
) -> bool | UnreadableAttributionPreference | None:
    """Load a saved choice, distinguishing absence from unreadable storage."""
    path = config_dir / "config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return UnreadableAttributionPreference(path, str(error))
    return classify_attribution_preference(config, path)


def write_attribution_preference(
    config_dir: Path,
    enabled: bool,
    trailer: str = _DEFAULT_TRAILER,
) -> None:
    """Write attribution preference, preserving other config keys."""
    config = read_global_config(config_dir)
    config["attribution"] = {
        "enabled": enabled,
        "trailer": trailer,
    }
    write_global_config(config_dir, config)


def _resolve_python_path() -> str:
    """Resolve Python interpreter path for hook shim.

    Delegates to the shared SSOT `resolve_python_path_for_shell()`
    (scripts/shared/install_paths.py) -- this used to be a standalone,
    byte-identical copy of the same logic duplicated in
    DESPlugin._resolve_python_path (des_plugin.py)
    (D3-code-duplication-resolve-python-path, techdebt.md). Kept as a
    thin delegating wrapper (rather than inlined at the two call sites)
    so existing callers/tests that import this module-level name keep
    working unchanged.
    """
    return resolve_python_path_for_shell()


def _resolve_hooks_dir() -> Path:
    """Resolve effective git hooks directory.

    Priority: ``core.hooksPath`` (unscoped, then global) > the shared
    ``.git/hooks`` directory resolved by ``resolve_hooks_dir`` (the
    worktree-aware default).

    Never returns ~/.nwave/hooks/ as default -- that would require setting
    global core.hooksPath which shadows pre-commit hooks in .git/hooks/.
    """
    # Try unscoped first -- returns effective value (local > global)
    for git_args in (
        ["git", "config", "core.hooksPath"],
        ["git", "config", "--global", "core.hooksPath"],
    ):
        try:
            result = subprocess.run(
                git_args,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                hooks_path = result.stdout.strip()
                # Expand ~ and $HOME
                hooks_path = os.path.expandvars(str(Path(hooks_path).expanduser()))
                return Path(hooks_path)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # No hooksPath configured -- delegate to the shared primitive that
    # resolves <git-common-dir>/hooks (worktree-aware). See
    # scripts/shared/git_hooks_paths.py and RCA Branch C.
    try:
        return resolve_hooks_dir()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        # Last resort: .git/hooks/ relative to cwd
        return Path(".git") / "hooks"


def _set_hooks_path(hooks_dir: Path) -> None:
    """No-op: retained for API compatibility only.

    Previously set git global core.hooksPath, which SHADOWED pre-commit
    hooks in .git/hooks/. Now the hook shim is installed directly into
    the effective hooks directory (resolved by _resolve_hooks_dir),
    so no global override is needed.
    """


@dataclass(frozen=True)
class GitDiscoveryFailure:
    """Repository discovery could not establish a hook location."""

    reason: str


def _git_output(cwd: Path, *args: str) -> str | GitDiscoveryFailure | None:
    """Read git output, preserving failures separately from an absent value."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return GitDiscoveryFailure(
            f"git did not answer within 5 s (5-second timeout): "
            f"git {' '.join(args)} in {cwd}"
        )
    except (subprocess.SubprocessError, OSError) as error:
        return GitDiscoveryFailure(f"git {' '.join(args)} in {cwd} failed: {error}")
    if result.returncode:
        if args == ("config", "core.hooksPath") and result.returncode == 1:
            return None
        reason = result.stderr.strip()
        if args == ("rev-parse", "--show-toplevel") and (
            result.returncode == 128 and "not a git repository" in reason.lower()
        ):
            return None
        return GitDiscoveryFailure(
            f"git {' '.join(args)} in {cwd} exited {result.returncode}: "
            f"{reason or 'no error detail was returned'}"
        )
    output = result.stdout.strip()
    if output or args == ("config", "core.hooksPath"):
        return output or None
    return GitDiscoveryFailure(f"git {' '.join(args)} in {cwd} returned no output")


def resolve_repository_hooks_dir(
    repository: Path,
) -> Path | GitDiscoveryFailure | None:
    """Effective hooks directory of the git work tree containing ``repository``.

    ``core.hooksPath`` (local > global) wins; otherwise the shared
    ``<git-common-dir>/hooks``. Returns None only for a non-repository; discovery
    failures carry their cause. Never sets or changes any git configuration.
    """
    toplevel = _git_output(repository, "rev-parse", "--show-toplevel")
    if isinstance(toplevel, GitDiscoveryFailure):
        return toplevel
    if toplevel is None:
        return None
    configured = _git_output(repository, "config", "core.hooksPath")
    if isinstance(configured, GitDiscoveryFailure):
        return configured
    if configured is not None:
        expanded = Path(os.path.expandvars(str(Path(configured).expanduser())))
        return expanded if expanded.is_absolute() else Path(toplevel) / expanded
    common_dir = _git_output(repository, "rev-parse", "--git-common-dir")
    if isinstance(common_dir, GitDiscoveryFailure):
        return common_dir
    if common_dir is None:
        return GitDiscoveryFailure("git returned no shared repository directory")
    return (repository / common_dir / "hooks").resolve()


def has_current_fallback(hooks_dir: Path) -> bool:
    """True when ``hooks_dir`` holds an executable shim carrying the fallback marker."""
    shim_path = hooks_dir / _HOOK_SHIM_NAME
    try:
        content = shim_path.read_text(encoding="utf-8")
        return FALLBACK_MARKER in content and os.access(shim_path, os.X_OK)
    except OSError:
        return False


def _with_fallback_marker(shim: str) -> str:
    """Insert the fallback marker as a comment right after the shebang line."""
    if FALLBACK_MARKER in shim:
        return shim
    first_line, _, rest = shim.partition("\n")
    return f"{first_line}\n# {FALLBACK_MARKER}\n{rest}"


def _read_shim_template() -> str:
    """Read the prepare-commit-msg shell shim template."""
    # Template is in nWave/templates/ relative to project root
    # At install time, it is copied to the installed location
    template_locations = [
        Path(__file__).parent.parent.parent
        / "nWave"
        / "templates"
        / "prepare-commit-msg.template",
        Path.home() / ".claude" / "templates" / "prepare-commit-msg.template",
    ]
    for loc in template_locations:
        if loc.exists():
            return loc.read_text(encoding="utf-8")

    # Fallback: inline template
    return (
        "#!/bin/sh\n"
        "# nWave attribution hook -- chains with existing hook\n"
        'HOOK_DIR="$(dirname "$0")"\n'
        'if [ -x "$HOOK_DIR/prepare-commit-msg.nwave-original" ]; then\n'
        '    "$HOOK_DIR/prepare-commit-msg.nwave-original" "$@" || exit $?\n'
        "fi\n"
        'if ! command -v "{{PYTHON_CMD}}" >/dev/null 2>&1; then\n'
        '    echo "nWave attribution: python3 not found, skipping" >&2\n'
        "    exit 0\n"
        "fi\n"
        '[ -f "{{HOOK_SCRIPT_PATH}}" ] || exit 0\n'
        '"{{PYTHON_CMD}}" "{{HOOK_SCRIPT_PATH}}" "$@"\n'
    )


def install_attribution_hook(config_dir: Path, hooks_dir: Path) -> Path:
    """Install prepare-commit-msg hook for attribution trailer.

    1. Write into the hooks directory the caller names (no git probe)
    2. Copy hook script to config_dir/hooks/
    3. If existing prepare-commit-msg, rename to .nwave-original
    4. Render and write shell shim as prepare-commit-msg
    5. Make executable

    Writes only under the two directories the caller names: no git probe, no
    working-directory lookup and no home-directory default. The caller resolves
    its repository's hooks directory and passes both paths in.

    Never sets global core.hooksPath -- the shim is installed directly
    into the caller's hooks directory to avoid shadowing pre-commit.

    Args:
        config_dir: nWave bookkeeping directory, for example ~/.nwave/.
        hooks_dir: Hooks directory that receives the shim, for example
            <repository>/.git/hooks/.

    Returns:
        Path to installed hook shim.
    """
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Copy hook script to config_dir/hooks/
    hook_dest_dir = config_dir / "hooks"
    hook_dest_dir.mkdir(parents=True, exist_ok=True)

    hook_source = Path(__file__).parent.parent / "hooks" / _HOOK_SCRIPT_NAME
    hook_dest = hook_dest_dir / _HOOK_SCRIPT_NAME
    if hook_source.exists():
        shutil.copy2(hook_source, hook_dest)

    # Handle existing prepare-commit-msg hook (chaining)
    shim_path = hooks_dir / _HOOK_SHIM_NAME
    original_path = hooks_dir / f"{_HOOK_SHIM_NAME}{ORIGINAL_SUFFIX}"

    if shim_path.exists():
        content = shim_path.read_text(encoding="utf-8")
        if "nwave_attribution_hook" in content:
            # Our shim already -- overwrite with updated version
            pass
        elif not original_path.exists():
            # Rename existing user hook to .nwave-original
            shim_path.rename(original_path)

    # Resolve paths for shim template, with shell-safety validation
    python_cmd = _resolve_python_path()
    if _SHELL_UNSAFE.search(python_cmd):
        python_cmd = "python3"  # fallback to safe default
    hook_script_path = str(hook_dest)
    if _SHELL_UNSAFE.search(hook_script_path):
        hook_script_path = str(config_dir / "hooks" / _HOOK_SCRIPT_NAME)
    home = str(Path.home())
    if hook_script_path.startswith(home):
        hook_script_path = "$HOME" + hook_script_path[len(home) :]

    # Render and write shim
    template = _read_shim_template()
    shim_content = template.replace("{{PYTHON_CMD}}", python_cmd)
    shim_content = shim_content.replace("{{HOOK_SCRIPT_PATH}}", hook_script_path)
    shim_content = _with_fallback_marker(shim_content)

    shim_path.write_text(shim_content, encoding="utf-8")
    shim_path.chmod(
        shim_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
    )

    # Record hooks_dir in config for deterministic uninstall
    config = read_global_config(config_dir)
    config.setdefault("attribution", {})["hooks_dir"] = str(hooks_dir)
    write_global_config(config_dir, config)

    return shim_path


def read_attribution_hooks_dir(config_dir: Path) -> str | None:
    """Read the recorded hook location before uninstall may delete its config."""
    recorded = _read_attribution_metadata(config_dir).get("hooks_dir")
    return recorded if isinstance(recorded, str) else None


def remove_attribution_hook(
    config_dir: Path | None = None,
    *,
    repository: Path,
    recorded_hooks_dir: str | None,
) -> tuple[str, ...]:
    """Retire known managed shims and disable attribution in unvisited repos.

    User hooks are preserved or restored. Known-directory failures are returned
    as warnings; runtime deletion still runs so surviving shims become inert.
    An unremovable runtime raises rather than claiming attribution is disabled.
    """
    config_dir = _default_config_dir(config_dir)
    directories = _candidate_hooks_dirs(recorded_hooks_dir, None, repository=repository)
    warnings: list[str] = []
    for directory in directories:
        shim = directory / _HOOK_SHIM_NAME
        original = directory / f"{_HOOK_SHIM_NAME}{ORIGINAL_SUFFIX}"
        try:
            content = shim.read_text(encoding="utf-8") if shim.exists() else None
            owned = content is not None and (
                "nwave_attribution_hook" in content or FALLBACK_MARKER in content
            )
            if owned:
                shim.unlink()
            if original.exists() and (owned or not shim.exists()):
                original.rename(shim)
        except (OSError, UnicodeError) as error:
            warnings.append(
                f"Attribution shim cleanup in {directory} could not complete: {error}. "
                "Resolve access to this directory, then retry `nwave-ai uninstall`. "
                "The shared attribution runtime is being removed so remaining "
                "nWave shims add no credit."
            )

    runtime = config_dir / "hooks" / _HOOK_SCRIPT_NAME
    try:
        runtime.unlink(missing_ok=True)
    except OSError as error:
        raise OSError(
            "\n".join(
                [
                    *warnings,
                    f"Attribution runtime {runtime} could not be removed: {error}. "
                    "Resolve access to this file and retry `nwave-ai uninstall`; "
                    "attribution may remain active until it is removed.",
                ]
            )
        ) from error
    return tuple(warnings)


# ---------------------------------------------------------------------------
# settings.json attribution surface (ADR-CA-004/005).
#
# Drives commit attribution through Claude Code's first-party
# ~/.claude/settings.json `attribution.{commit,pr}` surface, replacing the
# retired prepare-commit-msg git hook. The locked managed payload below is
# written verbatim and also serves as the idempotency baseline (H2).
# ---------------------------------------------------------------------------

NWAVE_MANAGED_COMMIT = (
    "🤖 Generated with Claude Code\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>\n"
    "Co-Authored-By: nWave <nwave@nwave.ai>"
)
NWAVE_MANAGED_PR = (
    "🤖 Generated with [Claude Code](https://claude.ai/code) — "
    "[nWave](https://github.com/nwaveai)"
)

# Classification of the current settings.json attribution.commit relative to
# the recorded baseline (H2).
ATTRIBUTION_FRESH = "fresh"  # no attribution.commit recorded
ATTRIBUTION_NWAVE_MANAGED = (
    "nwave_managed"  # matches last_written_value (safe to rewrite)
)
ATTRIBUTION_USER_MANAGED = "user_managed"  # the developer authored it (never stomp)
ATTRIBUTION_UNAVAILABLE = "unavailable"  # ~/.claude absent or settings.json corrupt

_SETTINGS_FILENAME = "settings.json"


def _default_claude_dir(claude_dir: Path | None) -> Path:
    """Resolve the Claude config directory (sandbox-aware via Path.home())."""
    return claude_dir if claude_dir is not None else Path.home() / ".claude"


def _default_config_dir(config_dir: Path | None) -> Path:
    """Resolve the nWave bookkeeping directory (sandbox-aware via Path.home())."""
    return config_dir if config_dir is not None else Path.home() / ".nwave"


def read_claude_settings(claude_dir: Path | None = None) -> dict | None:
    """Read ~/.claude/settings.json.

    Returns the parsed settings dict, an empty dict when ~/.claude/ exists but
    settings.json does not, or None when ~/.claude/ is absent (Q5: Claude Code
    not installed → caller warn+skips). Raises ValueError when settings.json
    exists but is not valid JSON, so the caller can warn+skip without stomping
    a corrupt file.
    """
    claude_dir = _default_claude_dir(claude_dir)
    if not claude_dir.exists():
        return None
    settings_path = claude_dir / _SETTINGS_FILENAME
    if not settings_path.exists():
        return {}
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"settings.json is not valid JSON: {exc}") from exc


def _write_settings_atomic(claude_dir: Path, settings: dict) -> None:
    """Atomically write settings.json (temp file + os.replace), 2-space indent,
    insertion order preserved, trailing newline (Q6/Q8)."""
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / _SETTINGS_FILENAME
    fd, tmp_name = tempfile.mkstemp(
        dir=str(claude_dir), prefix=".settings-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write("\n")
        Path(tmp_name).replace(settings_path)
    except BaseException:
        try:
            Path(tmp_name).unlink()
        except OSError:
            pass
        raise


def _read_attribution_metadata(config_dir: Path) -> dict:
    """Read optional legacy metadata without normalizing the saved preference."""
    config = read_global_config(config_dir)
    attribution = config.get("attribution") if isinstance(config, dict) else None
    return attribution if isinstance(attribution, dict) else {}


def classify_attribution_value(
    config_dir: Path | None = None,
    claude_dir: Path | None = None,
) -> str:
    """Classify the current attribution.commit relative to the recorded
    last_written_value (H2): "fresh" | "nwave_managed" | "user_managed" |
    "unavailable" (~/.claude absent or settings.json corrupt).

    A value matching the managed payload is treated as nWave-managed even when
    no baseline was recorded, so a re-install over a prior nWave write is
    idempotent.
    """
    try:
        settings = read_claude_settings(claude_dir)
    except ValueError:
        return ATTRIBUTION_UNAVAILABLE
    if settings is None:
        return ATTRIBUTION_UNAVAILABLE
    current = (settings.get("attribution") or {}).get("commit")
    if current is None:
        return ATTRIBUTION_FRESH

    last_written = _read_attribution_metadata(_default_config_dir(config_dir)).get(
        "last_written_value"
    )
    if current in (last_written, NWAVE_MANAGED_COMMIT):
        return ATTRIBUTION_NWAVE_MANAGED
    return ATTRIBUTION_USER_MANAGED


def write_settings_attribution(
    config_dir: Path | None = None,
    claude_dir: Path | None = None,
) -> bool:
    """Write the managed attribution.{commit,pr} block into settings.json.

    Idempotency/collision (H2/D4):
      - fresh / already-nWave-managed → write the managed payload (idempotent).
      - user-managed → leave the developer's value untouched; record it as
        previous_user_value for later restoration.

    Preserves all other settings.json keys (Q6 insertion order). Atomic write
    (Q8). Returns False (warn+skip) when ~/.claude/ is absent (Q5) or
    settings.json is corrupt — never stomps in those cases.
    """
    config_dir = _default_config_dir(config_dir)
    try:
        settings = read_claude_settings(claude_dir)
    except ValueError:
        return False
    if settings is None:
        return False

    classification = classify_attribution_value(config_dir, claude_dir)
    if classification == ATTRIBUTION_USER_MANAGED:
        user_value = (settings.get("attribution") or {}).get("commit")
        config = read_global_config(config_dir)
        attribution = config.setdefault("attribution", {})
        attribution["previous_user_value"] = user_value
        write_global_config(config_dir, config)
        return False

    attribution = settings.setdefault("attribution", {})
    attribution["commit"] = NWAVE_MANAGED_COMMIT
    attribution["pr"] = NWAVE_MANAGED_PR
    _write_settings_atomic(_default_claude_dir(claude_dir), settings)

    config = read_global_config(config_dir)
    book = config.setdefault("attribution", {})
    book["enabled"] = True
    book["last_written_value"] = NWAVE_MANAGED_COMMIT
    write_global_config(config_dir, config)
    return True


def remove_settings_attribution(
    config_dir: Path | None = None,
    claude_dir: Path | None = None,
) -> None:
    """Remove the managed attribution key from settings.json only when it still
    matches what nWave wrote; preserve a user-modified value untouched (H4).

    Leaves all neighbouring settings.json keys intact. No-op when ~/.claude/ is
    absent or the value is user-managed.
    """
    config_dir = _default_config_dir(config_dir)
    try:
        settings = read_claude_settings(claude_dir)
    except ValueError:
        return
    if settings is None:
        return

    classification = classify_attribution_value(config_dir, claude_dir)
    if classification != ATTRIBUTION_NWAVE_MANAGED:
        return

    attribution = settings.get("attribution")
    if isinstance(attribution, dict):
        attribution.pop("commit", None)
        attribution.pop("pr", None)
        if not attribution:
            settings.pop("attribution", None)
    _write_settings_atomic(_default_claude_dir(claude_dir), settings)

    config = read_global_config(config_dir)
    book = config.get("attribution") if isinstance(config, dict) else None
    if isinstance(book, dict) and not isinstance(
        read_attribution_preference(config_dir), UnreadableAttributionPreference
    ):
        book.pop("last_written_value", None)
        write_global_config(config_dir, config)


# ---------------------------------------------------------------------------
# Legacy settings.json attribution cleanup on upgrade (DDD-3).
#
# DDD-3 mandates a BEHAVIORAL contract (on upgrade, a nWave-written
# settings.json attribution.{commit,pr} block is removed while a user-modified
# value is preserved). This is the one-shot upgrade cleanup, parallel to
# migrate_legacy_hook (which retires the prepare-commit-msg shim). It REUSES the
# retained migration primitives classify_attribution_value (to decide whether the
# block is nWave-written) and remove_settings_attribution (the removal primitive,
# which itself classifies and only removes a nWave-managed value). The AB-4/AB-5
# behaviour is asserted through the real AttributionPlugin.install driving port.
# ---------------------------------------------------------------------------


def migrate_legacy_settings_attribution(
    config_dir: Path | None = None,
    claude_dir: Path | None = None,
) -> bool:
    """One-shot legacy settings.json attribution cleanup on upgrade (DDD-3).

    Contract: remove a previously nWave-written ``attribution.{commit,pr}`` block
    (classifier baseline = nWave-managed), preserve a user-modified value
    untouched, fail-open on absent/corrupt settings.json (warn+skip, never
    raise). Returns True only when a legacy nWave-managed block was cleaned.

    Reuses ``classify_attribution_value`` to recognise the nWave-managed baseline
    and ``remove_settings_attribution`` verbatim as the removal primitive (which
    is itself a no-op on absent/corrupt/user-managed settings, so fail-open and
    preserve-user are inherited rather than re-implemented).
    """
    classification = classify_attribution_value(config_dir, claude_dir)
    if classification != ATTRIBUTION_NWAVE_MANAGED:
        return False
    remove_settings_attribution(config_dir, claude_dir)
    return True


def _git_path(*args: str, cwd: Path | None = None) -> Path | None:
    """Run a fail-open ``git rev-parse`` probe, returning a Path or None.

    Any subprocess failure (git absent, not a repo, timeout) yields None so the
    caller can skip that candidate -- migration must never raise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", *args],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    path = Path(result.stdout.strip())
    return cwd / path if cwd is not None else path


def _effective_hookspath(cwd: Path | None = None) -> Path | None:
    """Effective (unscoped: local > global) ``core.hooksPath``, expanded.

    Fail-open: returns None when unset or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    raw = result.stdout.strip()
    path = Path(os.path.expandvars(str(Path(raw).expanduser())))
    return cwd / path if cwd is not None else path


def _candidate_hooks_dirs(
    recorded: str | None, git_dir: Path | None, *, repository: Path | None = None
) -> list[Path]:
    """Enumerate EVERY hooks dir git could resolve the shim into (root cause B).

    The shim must be removed wherever git would actually look for it, not just
    the bounded set (recorded config + ``_resolve_hooks_dir``) the pre-fix code
    scanned. A worktree, a local ``core.hooksPath``, a stale recorded value, or
    a shim installed via the historical ``--show-toplevel`` resolution all place
    the shim outside that bounded set, leaving it orphaned when its runtime
    target is deleted. Each git probe is fail-open; the result is de-duplicated
    by resolved absolute path while preserving discovery order.
    """
    candidates: list[Path | None] = []
    if recorded:
        candidates.append(Path(recorded))
    if git_dir is not None:
        candidates.append(git_dir / "hooks")
    else:
        if repository is None:
            try:
                candidates.append(_resolve_hooks_dir())
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                pass
        else:
            resolved = resolve_repository_hooks_dir(repository)
            if isinstance(resolved, Path):
                candidates.append(resolved)
            elif isinstance(resolved, GitDiscoveryFailure):
                print(
                    f"Attribution cleanup could not discover hooks in {repository}: "
                    f"{resolved.reason}. Recorded hook locations will still be checked.",
                    file=sys.stderr,
                )
        # Worktree-local hooks dir.
        candidates.append(_git_path("--git-path", "hooks", cwd=repository))
        # Toplevel .git/hooks -- the historical --show-toplevel target.
        toplevel = _git_path("--show-toplevel", cwd=repository)
        if toplevel is not None:
            candidates.append(toplevel / ".git" / "hooks")
        # Effective core.hooksPath (local > global).
        candidates.append(_effective_hookspath(cwd=repository))

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            key = candidate.resolve()
        except OSError:
            key = candidate
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def migrate_legacy_hook(
    config_dir: Path | None = None,
    claude_dir: Path | None = None,
    git_dir: Path | None = None,
    *,
    repository: Path | None = None,
) -> bool:
    """One-shot legacy-hook migration (H5/D6).

    Detects and dismantles the retired prepare-commit-msg shim: removes the
    shim, restores any chained .nwave-original, deletes the runtime copy in
    ~/.nwave/hooks/, and defensively unsets a historical global core.hooksPath
    that resolves to ~/.nwave/hooks/ (and only that value). Returns True when a
    legacy hook was found and dismantled.

    ``repository`` binds git discovery to a declared caller rather than the
    installer subprocess's working directory.
    """
    config_dir = _default_config_dir(config_dir)
    migrated = False

    # 1. Remove the shim from EVERY candidate hooks dir git could resolve. A
    #    shim carrying the fallback marker is the current fallback, not legacy:
    #    its directory is left untouched.
    recorded = _read_attribution_metadata(config_dir).get("hooks_dir")
    shim_dirs = _candidate_hooks_dirs(recorded, git_dir, repository=repository)
    current_fallback_kept = False

    for hooks_dir in shim_dirs:
        shim_path = hooks_dir / _HOOK_SHIM_NAME
        original_path = hooks_dir / f"{_HOOK_SHIM_NAME}{ORIGINAL_SUFFIX}"
        if has_current_fallback(hooks_dir):
            current_fallback_kept = True
            continue
        if shim_path.exists():
            try:
                content = shim_path.read_text(encoding="utf-8")
                if "nwave_attribution_hook" in content:
                    shim_path.unlink()
                    migrated = True
            except OSError:
                pass
        if original_path.exists():
            try:
                original_path.rename(shim_path)
            except OSError:
                pass

    # 2. Delete the runtime copy in ~/.nwave/hooks/ unless a current fallback
    #    shim still runs it.
    runtime = config_dir / "hooks" / _HOOK_SCRIPT_NAME
    if runtime.exists() and not current_fallback_kept:
        try:
            runtime.unlink()
            migrated = True
        except OSError:
            pass

    # 3. Defensively unset a historical core.hooksPath == ~/.nwave/hooks/ (D6).
    _reverse_historical_hookspath(config_dir)

    return migrated


def _reverse_historical_hookspath(config_dir: Path) -> None:
    """Unset global core.hooksPath only when it resolves to config_dir/hooks/.

    Leaves any other value (Husky, corporate, user-chosen) untouched (D6).
    """
    nwave_hooks = (config_dir / "hooks").resolve()
    try:
        result = subprocess.run(
            ["git", "config", "--global", "core.hooksPath"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return
    if result.returncode != 0 or not result.stdout.strip():
        return
    configured = result.stdout.strip()
    resolved = Path(os.path.expandvars(str(Path(configured).expanduser()))).resolve()
    if resolved != nwave_hooks:
        return
    try:
        subprocess.run(
            ["git", "config", "--global", "--unset", "core.hooksPath"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


# ---------------------------------------------------------------------------
# Legacy PreToolUse commit-attribution hook cleanup (ADR-CA-006 D6/D7/O-4).
#
# Removal of the retired independent hook registration (E7/DDD-3). The
# universal `pre-tool-use` adapter now handles all attribution decisions at
# runtime by reading attribution.enabled per invocation, so the dedicated
# `pre-commit-attribution` entry is no longer needed. On upgrade, this cleanup
# removes any stale entry. Tombstoned: the exact historical command that was
# registered, used only as the removal baseline.
# ---------------------------------------------------------------------------

# Unique marker comment that tagged the registered command (historical).
# Tombstoned: used only to identify and remove stale entries on upgrade.
_ATTRIBUTION_HOOK_MARKER = "# des-hook:pre-commit-attribution"


def _attribution_hook_command(claude_dir: Path) -> str:
    """Reconstruct the historical $HOME-portable attribution hook command.

    Exact replica of the legacy registration command, used only as the
    removal baseline for cleanup. Never called to register new hooks.
    The universal pre-tool-use adapter observes attribution.enabled at
    invocation time instead.
    """
    if claude_dir == Path.home() / ".claude":
        lib_path = "$HOME/.claude/lib/python"
    else:
        lib_path = str(claude_dir / "lib" / "python")
    python_cmd = _resolve_python_path()
    # Historical command text, split so the retired module path is never a
    # literal dotted name in a tracked source file; the joined string is the
    # byte-exact legacy registration the cleanup below must recognise.
    return (
        f"{_ATTRIBUTION_HOOK_MARKER}\n"
        f"PYTHONPATH={lib_path} {python_cmd} -m "
        f"des"
        f".adapters.drivers.hooks.claude_code_hook_adapter "
        f"pre-tool-use"
    )


def cleanup_legacy_attribution_hook(claude_dir: Path | None = None) -> bool:
    """Remove the stale independent attribution PreToolUse entry on upgrade.

    Scans ~/.claude/settings.json hooks.PreToolUse for nested hook dicts whose
    full `command` field matches the exact historical registration, removing
    ONLY those hooks. Preserves siblings (DES guards, user hooks), sibling
    metadata (timeout, entry-level keys), non-dicts, marker-only and near-match
    commands. Returns True when an entry was modified. No-op when settings.json
    is absent/corrupt; never raises.

    For each entry dict with list hooks:
    - Filter out hook dicts with exact-command match
    - If hooks remain after filter, append {**entry, "hooks": retained}
    - If no hooks remain, drop the entry entirely
    - Preserve untouched entries exactly
    Write to settings.json only if removed=True.
    """
    claude_dir = _default_claude_dir(claude_dir)
    try:
        settings = read_claude_settings(claude_dir)
    except ValueError:
        return False
    if settings is None:
        return False

    pre_tool_use = settings.get("hooks", {}).get("PreToolUse")
    if not isinstance(pre_tool_use, list):
        return False

    expected_command = _attribution_hook_command(claude_dir)
    removed = False
    final_entries = []

    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            final_entries.append(entry)
            continue

        hooks = entry.get("hooks")
        if not isinstance(hooks, list):
            final_entries.append(entry)
            continue

        # Filter out hooks with exact-command match.
        retained_hooks = []
        for hook in hooks:
            if isinstance(hook, dict) and hook.get("command") == expected_command:
                removed = True
            else:
                retained_hooks.append(hook)

        # Append entry if hooks remain, otherwise drop.
        if retained_hooks:
            final_entries.append({**entry, "hooks": retained_hooks})

    if not removed:
        return False

    settings["hooks"]["PreToolUse"] = final_entries
    _write_settings_atomic(claude_dir, settings)
    return True
