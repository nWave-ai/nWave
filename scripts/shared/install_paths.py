"""Centralized installation path constants -- single source of truth.

Replaces 10+ scattered hardcoded path constructions across installer
plugins, verifier, and build scripts.

All consumers should import from this module::

    from scripts.shared.install_paths import AGENTS_SUBDIR, agents_dir
"""

from __future__ import annotations

import os
import sys
from pathlib import Path, PureWindowsPath

from nwave_ai.hooks.registration import interpreter_for_shell
from nwave_ai.platform.locations import NWaveLocations
from nwave_ai.platform.result import Failure


def _standard_temp_roots() -> list[Path]:
    """The hand-maintained enumeration of standard ephemeral-directory roots.

    This is a DECLARED ENUMERATION, not a computed property -- "this
    directory will be cleaned up out from under a running process" is not
    something the filesystem can be asked; it is convention, platform by
    platform. A list that admits it is a list invites the next reader to
    add a case when a new convention shows up (e.g. a fifth OS, a new
    container runtime's scratch mount); dressing this up as something
    derived would instead convince them there is nothing left to add. Keep
    it a visible, literal list -- extend THIS function, never bolt a
    special case onto the caller.

    ``tempfile.gettempdir()`` is deliberately NOT consulted here, and
    exactly one candidate from it (a fresh boot's likely pick) is NOT
    equivalent to this list. ``gettempdir()`` returns exactly ONE root --
    whichever standard candidate was first writable when the interpreter
    started -- never the full set of standard ephemeral locations. A
    guard that keys on it alone leaves every OTHER standard root open: on
    a box where ``gettempdir()`` picked ``/tmp``, an interpreter rooted
    under ``/var/tmp`` or ``/usr/tmp`` -- equally standard, equally
    ephemeral -- would be judged durable. That is the exact
    one-known-bad-shape mistake this whole predicate exists to fix,
    reappearing one level down inside the function written to fix it.

    Worse, ``tempfile.gettempdir()`` has a documented LAST-RESORT
    fallback: when every standard root above is unwritable, it returns
    the process's OWN current working directory. Consulting it directly
    would then treat the CWD as ephemeral too -- on such a machine, EVERY
    interpreter under a developer's checkout (including its own
    ``.venv/bin/python``) would be rejected. This function's list never
    includes the CWD, on purpose: it enumerates ONLY genuine, named
    system/user ephemeral-directory conventions, sourced by hand rather
    than through the stdlib's own candidate search
    (``tempfile._candidate_tempdir_list()``, deliberately not imported --
    it is a private API that can change without notice, and importing it
    would import its CWD fallback entry right along with it, as if that
    were one of THIS guard's roots).

    Sources (named, not derived): the environment variables the stdlib
    itself consults first when set (``$TMPDIR``, ``$TEMP``, ``$TMP``, in
    that order), then the platform's standard directories: POSIX
    ``/tmp``, ``/var/tmp``, ``/usr/tmp``; Windows
    ``%LOCALAPPDATA%\\Temp``, ``%SYSTEMROOT%\\Temp``, ``C:\\TEMP``,
    ``C:\\TMP``, ``\\TEMP``, ``\\TMP``.

    The Windows six are NOT a uniform list, and this docstring says so
    rather than staying silent about it:

    - The first two (``%LOCALAPPDATA%\\Temp`` via ``Path.expanduser()``,
      ``%SYSTEMROOT%\\Temp`` via ``os.path.expandvars()``) are RESOLVED
      at call time into concrete, fully-qualified paths.
    - The last four (``C:\\Temp``, ``C:\\Tmp``, ``\\Temp``, ``\\Tmp``)
      are literal templates. ``is_durable_interpreter_path`` checks both
      their normalized lexical and their resolved physical forms.
    - Of those four, ``\\Temp`` and ``\\Tmp`` are DRIVE-RELATIVE, not
      absolute: Windows resolves a leading-backslash-no-drive path
      against whichever drive is current for the process, not
      necessarily ``C:``. This predicate does not special-case that
      resolution -- it relies on ``Path.resolve()`` to do whatever the
      OS itself would do with a drive-relative path, and does not verify
      the result on Windows (this module is authored and evaluated from
      a POSIX box). Documented here as a known, stated limitation rather
      than a silent gap: if drive-relative resolution ever proves wrong
      in practice, THIS is where to fix it, and the fix is either
      normalizing these two entries to a specific drive, or removing
      them and accepting narrower Windows coverage -- not silently
      trusting an unverified assumption.
    """
    roots: list[Path] = []
    for env_var in ("TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(env_var)
        if value:
            roots.append(Path(value))
    if sys.platform.startswith("win"):
        roots.extend(
            Path(candidate)
            for candidate in (
                Path(r"~\AppData\Local\Temp").expanduser(),
                os.path.expandvars(r"%SYSTEMROOT%\Temp"),
                r"C:\Temp",
                r"C:\Tmp",
                r"\Temp",
                r"\Tmp",
            )
        )
    else:
        roots.extend(Path(candidate) for candidate in ("/tmp", "/var/tmp", "/usr/tmp"))
    return roots


def is_durable_interpreter_path(path: str) -> bool:
    """Return True iff ``path`` is safe to persist for later execution.

    Answers ONLY the durability question -- will this path still exist
    when the persisted artifact (settings.json hook command, git shim,
    Copilot/Codex/OpenCode hook config) is invoked in the future? This is
    a DIFFERENT question from portability (whether the exact path is
    valid on a different machine): a ``$HOME``-rooted project ``.venv``
    is durable but not portable, and each call site's own ``.venv`` guard
    -- unchanged by this predicate -- answers that separate question.

    Rejects any path rooted under one of ``_standard_temp_roots()`` --
    see that function's docstring for why this is a hand-maintained
    enumeration rather than ``tempfile.gettempdir()`` alone, and why the
    current working directory is excluded from it on purpose.

    Both ``path`` and each candidate root are taken in TWO forms:
    normalized lexical (absolute, with ``.``/``..`` collapsed but symlinks
    retained) and resolved physical (``Path.resolve()``, with symlinks
    followed). All FOUR pairings are compared, not the two like-for-like
    ones: a lexical candidate under a resolved root is the macOS case where
    ``$TMPDIR`` is spelled ``/var/folders/...`` while the same directory
    resolves to ``/private/var/folders/...``, and comparing lexical to
    lexical and physical to physical alone lets an ephemeral launcher pass
    when BOTH halves hold, a resolved spelling AND an interpreter symlink
    pointing at a durable binary: the lexical form misses the alias and the
    physical form follows the symlink out of the temporary directory. The
    resolved spelling alone was already caught, because ``resolve()`` of a
    path with no symlink normalizes to itself. Do not reduce any comparison
    to a plain ``str.startswith`` check.

    Known gap, measured and deliberately not closed here: only the whole
    path's two forms are examined, so a durable-looking path whose
    INTERMEDIATE component symlinks into a temporary root, with a durable
    final target, is still judged durable although it breaks once that
    directory is cleaned up.
    """
    if not path:
        return False

    # A Windows absolute path is not a POSIX relative path merely because an
    # installer test happens to run on Linux. On Windows itself, keep the
    # platform-native resolution below so its declared temporary roots are
    # still rejected. On a non-Windows host, no POSIX filesystem judgment can
    # decide whether C:/... is durable; preserve it for the Windows consumer.
    if PureWindowsPath(path).is_absolute() and os.name != "nt":
        return True

    # ``Path.resolve`` is wrong here: it would dereference the symlink whose
    # lexical location this branch must retain. ``abspath`` normalizes ``..``.
    lexical_candidate = Path(os.path.abspath(path))  # noqa: PTH100
    physical_candidate = Path(path).resolve()
    for root in _standard_temp_roots():
        lexical_root = Path(os.path.abspath(root))  # noqa: PTH100
        physical_root = root.resolve()
        # Every pairing, not just like-for-like: on macOS a per-user $TMPDIR is
        # spelled /var/folders/... while the same directory resolves to
        # /private/var/folders/..., so a LEXICAL candidate under the resolved
        # spelling matches only the PHYSICAL root. Comparing lexical-to-lexical
        # and physical-to-physical alone lets an ephemeral launcher whose
        # symlink points at a durable binary pass both checks: the lexical form
        # misses the alias and the physical form follows the symlink out of the
        # temporary directory altogether.
        for candidate in (lexical_candidate, physical_candidate):
            for candidate_root in (lexical_root, physical_root):
                if candidate == candidate_root or candidate_root in candidate.parents:
                    return False
    return True


# Relative path segments (appended to claude_dir by callers)
AGENTS_SUBDIR = Path("agents") / "nw"
SKILLS_SUBDIR = Path("skills")
TEMPLATES_SUBDIR = Path("templates")
DES_LIB_SUBDIR = Path("lib") / "python" / "des"
SCRIPTS_SUBDIR = Path("scripts")
COMMANDS_LEGACY_SUBDIR = Path("commands") / "nw"  # deprecated, cleanup only
MANIFEST_FILENAME = "nwave-manifest.txt"
CONFIG_FILENAME = "config.json"
# Compatibility spelling for callers being migrated. New code must import
# CONFIG_FILENAME; the retired filename is only a ConfigWriter migration input.
GLOBAL_CONFIG_FILENAME = CONFIG_FILENAME
INSTALL_LOCK_FILENAME = "install.lock"


def env_or_none(environment_variable: str) -> str | None:
    """Return a non-empty environment value, treating empty as absent."""
    value = os.environ.get(environment_variable)
    return value or None


def agents_home() -> Path:
    """Return the install root every platform target of one invocation shares.

    The selected home is resolved by ``NWaveLocations.resolve`` -- the shared
    authority used by the installer, CLI, doctor, and hooks -- so this legacy
    convenience function cannot reimplement the override rule.
    """
    locations = NWaveLocations.resolve(
        home=Path.home(),
        repo_root=Path.cwd(),
        agents_home_override=env_or_none("NWAVE_AGENTS_HOME"),
        claude_config_override=env_or_none("CLAUDE_CONFIG_DIR"),
        codex_config_override=env_or_none("CODEX_HOME"),
    )
    # This convenience reader has historically been total.  The installer
    # itself observes a Failure and refuses before writing; read-only callers
    # retain their native-home fallback while never reimplementing selection.
    if isinstance(locations, Failure):
        return Path.home()
    return locations.unwrap().agents_home


def codex_config_dir(home_dir: Path | None = None) -> Path:
    """Resolve CODEX_HOME at the boundary, with an injectable default home."""
    override = env_or_none("CODEX_HOME")
    home = home_dir if home_dir is not None else Path.home()
    return Path(override) if override else home / ".codex"


# Devin CLI config root. Devin CLI stores its user-global config under
# ~/.config/devin/ on Linux/macOS (documented in devin extensibility docs).
# DEVIN_CONFIG_DIR is an nWave-level override for test isolation; Devin CLI
# itself has no published env var for relocating this directory.

DEVIN_CONFIG_DIR_ENV = "DEVIN_CONFIG_DIR"


def devin_config_dir() -> Path:
    """Return the Devin CLI configuration root, honoring DEVIN_CONFIG_DIR.

    Uses ~/.config/devin/ by default (the canonical Devin CLI path on
    Linux/macOS). DEVIN_CONFIG_DIR may be set for install isolation in tests.
    """
    override = env_or_none(DEVIN_CONFIG_DIR_ENV)
    return Path(override) if override else Path.home() / ".config" / "devin"


def devin_skills_dir() -> Path:
    """Return the Devin CLI global skills directory.

    Devin CLI discovers user-global skills at <config-root>/skills/.
    """
    return devin_config_dir() / "skills"


# OMP (oh-my-pi) native roots. OMP 18.5 resolves TWO DIFFERENT roots, and the
# installer must follow each faithfully:
#
# - Native SKILLS discovery follows PI_CODING_AGENT_DIR: the skill tree is
#   <PI_CODING_AGENT_DIR>/skills when that override is set (non-empty), else
#   <config-root>/agent/skills.
# - TASK-AGENT discovery follows the generic config root: agents are
#   <config-root>/agent/agents/*.md where the config root is
#   $HOME/<PI_CONFIG_DIR or ".omp"> -- PI_CODING_AGENT_DIR does NOT relocate
#   the agent-file root (empirical probe 2026-10-03: agent files written under
#   $PI_CODING_AGENT_DIR/agents are never discovered).
#
# NWAVE_AGENTS_HOME relocates the home root for install isolation, exactly as
# for every other platform target; PI_CONFIG_DIR renames the config root under
# that home exactly as OMP itself resolves it. The split is resolved ONCE,
# here, so every consumer (detector, plugins, receipt) shares one resolution.
OMP_CONFIG_DIR_ENV = "PI_CONFIG_DIR"
OMP_AGENT_DIR_ENV = "PI_CODING_AGENT_DIR"


def omp_config_root(home_dir: Path | None = None) -> Path:
    """Return the OMP config root, honoring NWAVE_AGENTS_HOME and PI_CONFIG_DIR.

    NWAVE_AGENTS_HOME relocates the home root for install isolation (the same
    override every other platform target honors); PI_CONFIG_DIR renames the
    config root under that home exactly as OMP itself resolves it.
    An explicit home takes precedence over the ambient install-home override
    so diagnostics inspect their caller's filesystem root.
    """
    home_override = env_or_none("NWAVE_AGENTS_HOME")
    home = (
        home_dir
        if home_dir is not None
        else Path(home_override)
        if home_override
        else Path.home()
    )
    return home / (env_or_none(OMP_CONFIG_DIR_ENV) or ".omp")


def omp_agent_dir(home_dir: Path | None = None) -> Path:
    """Return the OMP native agent directory (config root's ``agent/``).

    The task-agent discovery root -- the directory whose ``agents/`` and
    (when no PI_CODING_AGENT_DIR override is set) ``skills/`` OMP reads.
    """
    return omp_config_root(home_dir) / "agent"


def omp_agents_dir() -> Path:
    """Return the OMP native task-agent directory.

    Follows the generic config root: OMP's task-agent discovery never reads
    PI_CODING_AGENT_DIR for agent files.
    """
    return omp_agent_dir() / "agents"


def omp_skills_dir(home_dir: Path | None = None) -> Path:
    """Return the OMP native skills directory.

    Native skill discovery follows PI_CODING_AGENT_DIR: a non-empty override
    relocates the skills root to ``<override>/skills``; otherwise the skills
    tree lives under the config-root agent directory.
    """
    override = env_or_none(OMP_AGENT_DIR_ENV)
    if override:
        return Path(override) / "skills"
    return omp_agent_dir(home_dir) / "skills"


def omp_extensions_dir(home_dir: Path | None = None) -> Path:
    """Return the native extension root alongside the resolved skills tree."""
    return omp_skills_dir(home_dir).parent / "extensions"


def nwave_config_dir() -> Path:
    """Return the global nWave state root for this install destination."""
    return agents_home() / ".nwave"


def install_lock_path(home: Path | None = None) -> Path:
    """Return the exclusive-install lock file for one install destination.

    Scope is the install ROOT (``home``, default :func:`agents_home`), NOT the
    machine: two installs aimed at genuinely disjoint destinations -- an
    isolated lane pinning ``NWAVE_AGENTS_HOME``/``HOME`` -- must not serialize
    each other, while two installs aimed at the same root must. Every platform
    target of a single invocation (Claude, Codex, OpenCode, Copilot) resolves
    its write destinations beneath this one root, so one lock per root covers
    the whole invocation.
    """
    return (home or agents_home()) / ".nwave" / INSTALL_LOCK_FILENAME


def host_neutral_runtime_dir() -> Path:
    """Return the shared DES runtime root, independent of any host adapter."""
    return nwave_config_dir() / "runtime"


def active_runtime_pointer_path() -> Path:
    """Return the pointer file naming the runtime dir the des shim must use.

    The installer rewrites this file on EVERY install (see
    DESPlugin._install_des_module), recording the primary runtime python dir
    it just populated. The installed des/des-commit shims follow it, so the
    launcher always binds the runtime of the most recent install -- a
    Codex-only install can no longer leave a stale Claude-scoped launcher
    answering on PATH ("codex manifest green but launcher claude").
    """
    return nwave_config_dir() / "active-runtime"


def record_active_runtime(runtime_python_dir: Path) -> Path:
    """Record ``runtime_python_dir`` as the runtime the des shims resolve.

    Last install wins, deterministically. The shim validates the recorded
    dir still contains a ``des`` package before trusting it, so a later
    uninstall leaves a dangling pointer inert rather than fatal.
    """
    pointer = active_runtime_pointer_path()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(runtime_python_dir.as_posix() + "\n")
    return pointer


def agents_dir(claude_dir: Path) -> Path:
    """Return the agents installation directory."""
    return claude_dir / AGENTS_SUBDIR


def skills_dir(claude_dir: Path) -> Path:
    """Return the skills installation directory."""
    return claude_dir / SKILLS_SUBDIR


def templates_dir(claude_dir: Path) -> Path:
    """Return the templates installation directory."""
    return claude_dir / TEMPLATES_SUBDIR


def des_dir(claude_dir: Path) -> Path:
    """Return the DES library installation directory."""
    return claude_dir / DES_LIB_SUBDIR


def manifest_path(claude_dir: Path) -> Path:
    """Return the installation manifest file path."""
    return claude_dir / MANIFEST_FILENAME


# -- Python command resolution ------------------------------------------------

# Literal pattern used in source templates for portable Python resolution.
# Installed files replace this with the resolved concrete path.
PYTHON_CMD_SUBSTITUTION = "$(command -v python3 || command -v python)"


def resolve_python_command() -> str:
    """Return the base Python command name for skill/command templates.

    Returns 'python3' unconditionally. Templates that consume this value
    are rendered into markdown documents that run in contexts with PATH
    resolution, so the base command name is what callers want -- never
    an absolute path.

    For contexts that need an absolute path (non-shell spawn), see
    resolve_python_command_for_spawn(). For $HOME-prefixed paths in
    shell-execution contexts (settings.json hook commands), see
    resolve_python_path_for_shell().
    """
    return "python3"


def resolve_python_command_for_spawn() -> str:
    """Return an absolute forward-slash path to the current Python interpreter.

    Use when the consuming code spawns the interpreter without a shell:
    TypeScript Bun.spawn, Node child_process.spawn, Python subprocess.run
    without shell=True, posix_spawn/CreateProcess directly.

    Cross-platform safety: uses Path.as_posix() so the result contains no
    backslashes on any platform. This lets the path embed safely into a
    TypeScript double-quoted string literal without triggering escape-
    sequence interpretation (e.g. \\U unicode escape, \\n newline).
    Windows APIs accept forward-slash paths since Windows 2000.

    The .venv fallback is preserved: when the installer runs from a
    project-local virtual environment (development, CI), returns 'python3'
    to avoid leaking development paths into user-installed artifacts.

    For shell-execution contexts (settings.json hook commands, bash
    scripts where $HOME is expanded), use resolve_python_path_for_shell()
    instead.
    For markdown templates consumed by various runtimes, use
    resolve_python_command() (basename-only) instead.
    """
    python_path = sys.executable
    if not is_durable_interpreter_path(python_path):
        return "python3"
    if "/.venv/" in python_path or "\\.venv\\" in python_path:
        return "python3"
    return (
        PureWindowsPath(python_path).as_posix()
        if "\\" in python_path
        else Path(python_path).as_posix()
    )


def resolve_des_lib_path_for_spawn() -> str:
    """Return an absolute forward-slash path to the DES library directory.

    Same rationale as resolve_python_command_for_spawn: consumers pass
    this to non-shell contexts (Bun.spawn env vars setting PYTHONPATH,
    Python subprocess.run without shell=True) where shell variable
    expansion does NOT happen, so '$HOME' stays literal and must be
    resolved at install time.
    """
    return host_neutral_runtime_dir().as_posix()


def resolve_python_path_for_shell(*, windows: bool | None = None) -> str:
    """Resolve the Python interpreter path for shell-execution contexts
    (settings.json hook commands, git hook shims).

    Captures sys.executable and makes it portable by replacing the home
    directory prefix with $HOME (expanded by the shell at invocation time,
    unlike resolve_python_command_for_spawn's non-shell forward-slash form).

    Two independent guards fall back to 'python3':
    - Durability: the interpreter is rooted under a known-ephemeral
      location (tempfile.gettempdir()) and could be reaped before a
      hook ever fires. See is_durable_interpreter_path().
    - Portability: the current Python is a project-local .venv (e.g.
      during development) -- that exact path would not exist on a
      different machine, so it must not leak into a persisted artifact.

    This is the single source of truth for what were two independently
    hand-maintained, byte-identical copies of this logic:
    scripts/install/plugins/des_plugin.py DESPlugin._resolve_python_path
    (settings.json hook commands) and scripts/install/attribution_utils.py
    _resolve_python_path (git prepare-commit-msg shim) -- both now delegate
    here instead of reimplementing (D3-code-duplication-resolve-python-path,
    techdebt.md).
    """
    windows = os.name == "nt" if windows is None else windows
    python_path = sys.executable

    # Durability: reject interpreters rooted in a known-ephemeral location
    if not is_durable_interpreter_path(python_path):
        return "python3"

    # Portability: project-local .venv must not leak into a persisted artifact
    if "/.venv/" in python_path or "\\.venv\\" in python_path:
        return "python3"

    # Spell both sides in the shell's form before the $HOME prefix test: a
    # Windows backslash path never starts with a POSIX-spelled home otherwise.
    spelled = interpreter_for_shell(python_path, windows=windows)
    home = interpreter_for_shell(str(Path.home()), windows=windows)
    if spelled.startswith(home):
        spelled = "$HOME" + spelled[len(home) :]
    return spelled
