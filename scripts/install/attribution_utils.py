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
from pathlib import Path

from scripts.shared.git_hooks_paths import resolve_hooks_dir


_SHELL_UNSAFE = re.compile(r"[;&|`(){}]")


_DEFAULT_TRAILER = "Co-Authored-By: nWave <nwave@nwave.ai>"
_HOOK_SCRIPT_NAME = "nwave_attribution_hook.py"
_HOOK_SHIM_NAME = "prepare-commit-msg"
_HOOK_ORIGINAL_SUFFIX = ".nwave-original"


def read_global_config(config_dir: Path) -> dict:
    """Read global-config.json, returning empty dict on error."""
    config_file = config_dir / "global-config.json"
    try:
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def write_global_config(config_dir: Path, config: dict) -> None:
    """Write global-config.json with read-modify-write to preserve other keys."""
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "global-config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def read_attribution_preference(config_dir: Path) -> bool | None:
    """Read attribution preference from global config.

    Returns:
        True if enabled, False if disabled, None if not yet asked.
    """
    config = read_global_config(config_dir)
    attribution = config.get("attribution")
    if attribution is None:
        return None
    return attribution.get("enabled", False)


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

    Same pattern as DESPlugin._resolve_python_path():
    captures sys.executable, replaces $HOME for portability,
    falls back to 'python3' for project-local .venv paths.
    """
    python_path = sys.executable

    if "/.venv/" in python_path or "\\.venv\\" in python_path:
        return "python3"

    home = str(Path.home())
    if python_path.startswith(home):
        python_path = "$HOME" + python_path[len(home) :]
    return python_path


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


def install_attribution_hook(
    config_dir: Path | None = None,
    git_dir: Path | None = None,
) -> Path:
    """Install prepare-commit-msg hook for attribution trailer.

    1. Resolve hooks directory from git config (or .git/hooks/ default)
    2. Copy hook script to ~/.nwave/hooks/
    3. If existing prepare-commit-msg, rename to .nwave-original
    4. Render and write shell shim as prepare-commit-msg
    5. Make executable

    Never sets global core.hooksPath -- the shim is installed directly
    into the effective hooks directory to avoid shadowing pre-commit.

    Args:
        config_dir: Override for ~/.nwave/ (testing).
        git_dir: Explicit path to the .git directory. When provided, the
            hook shim is written to ``git_dir / "hooks"`` and the git
            config probe (``git rev-parse`` / ``git config
            core.hooksPath``) is skipped entirely. Primarily for tests
            that must guarantee isolation from the surrounding
            repository.

    Returns:
        Path to installed hook shim.
    """
    if config_dir is None:
        config_dir = Path.home() / ".nwave"

    hooks_dir = git_dir / "hooks" if git_dir is not None else _resolve_hooks_dir()
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
    original_path = hooks_dir / f"{_HOOK_SHIM_NAME}{_HOOK_ORIGINAL_SUFFIX}"

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

    shim_path.write_text(shim_content, encoding="utf-8")
    shim_path.chmod(
        shim_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
    )

    # Record hooks_dir in config for deterministic uninstall
    config = read_global_config(config_dir)
    config.setdefault("attribution", {})["hooks_dir"] = str(hooks_dir)
    write_global_config(config_dir, config)

    return shim_path


def remove_attribution_hook(config_dir: Path | None = None) -> None:
    """Remove attribution hook and restore original if chained.

    Resolves the hooks directory via the same shared primitive used at
    install time (``_resolve_hooks_dir``, which honours ``core.hooksPath``
    and otherwise delegates to the worktree-aware
    ``scripts.shared.git_hooks_paths.resolve_hooks_dir``). The
    ``attribution.hooks_dir`` value previously written into
    ``~/.nwave/global-config.json`` is consulted only as a back-stop for
    pre-existing installs whose absolute path was recorded there; if it
    is missing or relative, the live resolution wins. This is the RCA
    Branch C permanent fix: install and uninstall must agree on the
    hooks directory regardless of what stale config holds.

    Args:
        config_dir: Override for ~/.nwave/ (testing).
    """
    if config_dir is None:
        config_dir = Path.home() / ".nwave"

    # Authoritative resolution via the shared helper (worktree-aware).
    hooks_dir = _resolve_hooks_dir()

    # Back-stop: if a previous install recorded an ABSOLUTE hooks_dir
    # in config and that directory still exists, prefer it. This guards
    # against the rare case where the user reconfigured ``core.hooksPath``
    # between install and uninstall, leaving the original shim orphaned.
    config = read_global_config(config_dir)
    recorded = config.get("attribution", {}).get("hooks_dir")
    if recorded:
        recorded_path = Path(recorded)
        if recorded_path.is_absolute() and recorded_path.is_dir():
            hooks_dir = recorded_path

    shim_path = hooks_dir / _HOOK_SHIM_NAME
    original_path = hooks_dir / f"{_HOOK_SHIM_NAME}{_HOOK_ORIGINAL_SUFFIX}"

    # Only remove if it is our shim
    if shim_path.exists():
        try:
            content = shim_path.read_text(encoding="utf-8")
            if "nwave_attribution_hook" in content:
                shim_path.unlink()
        except OSError:
            pass

    # Restore original hook if it exists
    if original_path.exists():
        try:
            original_path.rename(shim_path)
        except OSError:
            pass


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

    gconf = read_global_config(_default_config_dir(config_dir))
    last_written = (gconf.get("attribution") or {}).get("last_written_value")
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
    book = config.get("attribution")
    if isinstance(book, dict):
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


def _git_path(*args: str) -> Path | None:
    """Run a fail-open ``git rev-parse`` probe, returning a Path or None.

    Any subprocess failure (git absent, not a repo, timeout) yields None so the
    caller can skip that candidate -- migration must never raise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _effective_hookspath() -> Path | None:
    """Effective (unscoped: local > global) ``core.hooksPath``, expanded.

    Fail-open: returns None when unset or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    raw = result.stdout.strip()
    return Path(os.path.expandvars(str(Path(raw).expanduser())))


def _candidate_hooks_dirs(recorded: str | None, git_dir: Path | None) -> list[Path]:
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
        try:
            candidates.append(_resolve_hooks_dir())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            pass
        # Worktree-local hooks dir.
        candidates.append(_git_path("--git-path", "hooks"))
        # Toplevel .git/hooks -- the historical --show-toplevel target.
        toplevel = _git_path("--show-toplevel")
        if toplevel is not None:
            candidates.append(toplevel / ".git" / "hooks")
        # Effective core.hooksPath (local > global).
        candidates.append(_effective_hookspath())

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
) -> bool:
    """One-shot legacy-hook migration (H5/D6).

    Detects and dismantles the retired prepare-commit-msg shim: removes the
    shim, restores any chained .nwave-original, deletes the runtime copy in
    ~/.nwave/hooks/, and defensively unsets a historical global core.hooksPath
    that resolves to ~/.nwave/hooks/ (and only that value). Returns True when a
    legacy hook was found and dismantled.
    """
    config_dir = _default_config_dir(config_dir)
    migrated = False

    # 1. Remove the shim from EVERY candidate hooks dir git could resolve.
    config = read_global_config(config_dir)
    recorded = (config.get("attribution") or {}).get("hooks_dir")
    shim_dirs = _candidate_hooks_dirs(recorded, git_dir)

    for hooks_dir in shim_dirs:
        shim_path = hooks_dir / _HOOK_SHIM_NAME
        original_path = hooks_dir / f"{_HOOK_SHIM_NAME}{_HOOK_ORIGINAL_SUFFIX}"
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

    # 2. Delete the runtime copy in ~/.nwave/hooks/.
    runtime = config_dir / "hooks" / _HOOK_SCRIPT_NAME
    if runtime.exists():
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
# PreToolUse commit-attribution hook registration (ADR-CA-006 D6/D7/O-4).
#
# The net-new E7 surface: install (and `nwave-ai attribution on|off`) register/
# remove a `Bash`/`pre-commit-attribution` PreToolUse entry in
# ~/.claude/settings.json, gated by `attribution.enabled`, COEXISTING with the
# existing DES `pre-bash` execution-log guard (append, never replace). The entry
# routes to the (E6-extended) `claude_code_hook_adapter pre-tool-use` adapter,
# whose `handle_pre_tool_use` calls `emit_commit_attribution_mutation` on Bash
# `git commit` commands. Mirrors the DES hook-registration pattern in
# des_plugin.py: $HOME-based command for cross-machine portability, a unique
# marker comment, atomic write, append-never-replace, idempotent.
# ---------------------------------------------------------------------------

# The action token tagging the commit-attribution PreToolUse entry, so it is
# recognizable and removable independently of the `pre-bash` guard.
ATTRIBUTION_HOOK_ACTION = "pre-commit-attribution"

# Unique marker comment prefixing the registered command. Mirrors the DES
# `# des-hook:pre-bash` convention so the entry is identifiable and removable
# without touching the DES guards or any operator-authored hook.
_ATTRIBUTION_HOOK_MARKER = f"# des-hook:{ATTRIBUTION_HOOK_ACTION}"

# PreToolUse adapter action that routes to handle_pre_tool_use ->
# emit_commit_attribution_mutation (hook_router maps "pre-tool-use").
_ATTRIBUTION_ADAPTER_ACTION = "pre-tool-use"


def _attribution_hook_command(claude_dir: Path) -> str:
    """Build the $HOME-portable PreToolUse command for the attribution entry.

    Mirrors DESPlugin._generate_hook_command: PYTHONPATH points at the installed
    lib, the interpreter is resolved portably ($HOME form for the default
    ~/.claude, absolute otherwise), and the adapter is invoked with the
    `pre-tool-use` action so handle_pre_tool_use -> emit_commit_attribution_mutation
    runs on Bash git-commit commands. The marker comment makes the entry
    identifiable and independently removable.
    """
    if claude_dir == Path.home() / ".claude":
        lib_path = "$HOME/.claude/lib/python"
    else:
        lib_path = str(claude_dir / "lib" / "python")
    python_cmd = _resolve_python_path()
    return (
        f"{_ATTRIBUTION_HOOK_MARKER}\n"
        f"PYTHONPATH={lib_path} {python_cmd} -m "
        f"des.adapters.drivers.hooks.claude_code_hook_adapter "
        f"{_ATTRIBUTION_ADAPTER_ACTION}"
    )


def _is_attribution_hook_entry(entry: dict) -> bool:
    """Whether a hooks.PreToolUse entry is the commit-attribution entry."""
    if not isinstance(entry, dict):
        return False
    return any(
        _ATTRIBUTION_HOOK_MARKER in hook.get("command", "")
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict)
    )


def register_attribution_hook(
    enabled: bool,
    claude_dir: Path | None = None,
) -> bool:
    """Register the Bash commit-attribution PreToolUse hook when enabled.

    When ``enabled`` is True, append a ``Bash``-matcher PreToolUse entry routing
    to the ``pre-tool-use`` adapter (tagged ``pre-commit-attribution``) into
    ``~/.claude/settings.json hooks.PreToolUse``, preserving every existing entry
    (the DES ``pre-bash`` guard and any operator-authored hook) and never
    duplicating on re-run. When ``enabled`` is False, ensure no such entry is
    present. Warn+skip (return False) when ``~/.claude`` is absent or
    ``settings.json`` is corrupt — never stomp.

    Returns True when an entry is registered, False otherwise (gate closed,
    config absent/corrupt).
    """
    if not enabled:
        unregister_attribution_hook(claude_dir)
        return False

    claude_dir = _default_claude_dir(claude_dir)
    try:
        settings = read_claude_settings(claude_dir)
    except ValueError:
        # Corrupt settings.json — warn+skip, never stomp.
        return False
    if settings is None:
        # ~/.claude absent (Claude Code not installed) — warn+skip.
        return False

    hooks = settings.setdefault("hooks", {})
    pre_tool_use = hooks.setdefault("PreToolUse", [])

    # Idempotent: never duplicate on re-register.
    if any(_is_attribution_hook_entry(entry) for entry in pre_tool_use):
        return True

    pre_tool_use.append(
        {
            "matcher": "Bash",
            "hooks": [
                {
                    "type": "command",
                    "command": _attribution_hook_command(claude_dir),
                }
            ],
        }
    )
    _write_settings_atomic(claude_dir, settings)
    return True


def unregister_attribution_hook(claude_dir: Path | None = None) -> None:
    """Remove ONLY the commit-attribution PreToolUse entry from settings.json.

    Leaves the DES ``pre-bash`` guard and every other PreToolUse entry intact
    (remove the attribution entry, never the guards). No-op when ``~/.claude`` is
    absent or the entry is not present.
    """
    claude_dir = _default_claude_dir(claude_dir)
    try:
        settings = read_claude_settings(claude_dir)
    except ValueError:
        # Corrupt settings.json — leave untouched.
        return
    if settings is None:
        return

    pre_tool_use = settings.get("hooks", {}).get("PreToolUse")
    if not isinstance(pre_tool_use, list):
        return

    remaining = [
        entry for entry in pre_tool_use if not _is_attribution_hook_entry(entry)
    ]
    if len(remaining) == len(pre_tool_use):
        # Nothing to remove — idempotent no-op (skip the write entirely).
        return

    settings["hooks"]["PreToolUse"] = remaining
    _write_settings_atomic(claude_dir, settings)
