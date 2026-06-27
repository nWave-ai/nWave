"""Wave-agnostic, base-agnostic execution-log path resolver.

Resolves the execution-log.json path for a DES project without hardcoding
either the docs BASE prefix or the WAVE subdirectory.

Base discovery (p2 — when *cwd* is given): search candidate bases under cwd
in order, preferring the override base docs/nwave/feature over the legacy
default docs/feature. The base is OBSERVED from the log already on disk,
never reconstructed from an AGENTS.md override the hook cannot read.

Wave resolution (p1 — within a single base):
1. If {base}/{project_id}/deliver/execution-log.json exists → use it
   (preserves backward compat for DELIVER-wave — the common case is fast).
2. Else glob {base}/{project_id}/*/execution-log.json:
   - Exactly 1 match → use it
   - 0 matches → raise FileNotFoundError
   - 2+ matches → raise ValueError (ambiguous; cannot determine active wave)

Root cause fixed:
    DES-PROJECT-ID encodes only the feature id — neither the docs base nor the
    wave subdirectory. subagent_stop_handler.py and deliver_progress_handler.py
    previously hardcoded docs/feature + deliver/ as those missing segments — a
    relic of the DELIVER-only, single-base era. Override-namespaced projects
    (docs/nwave/feature) and non-deliver waves write logs elsewhere.
"""

from pathlib import Path


_DEFAULT_BASE = Path("docs") / "feature"

# Ordered base suffixes searched when discovering the docs base from cwd.
# The non-default override base (docs/nwave/feature) is preferred over the
# legacy default (docs/feature): the base is OBSERVED from the log on disk,
# never reconstructed by hardcoding. When a project dual-writes to both bases
# (§10 legacy mirror), the override base wins instead of raising ambiguity.
_BASE_SUFFIXES = (
    Path("docs") / "nwave" / "feature",
    Path("docs") / "feature",
)


def resolve_execution_log_path(
    project_id: str,
    base: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Return the execution-log.json path for *project_id*.

    Args:
        project_id: The feature identifier (value of DES-PROJECT-ID marker).
        base: Parent directory containing per-project directories. When given,
              only this base is searched (backward-compatible single-base mode).
              Defaults to docs/feature (relative to cwd) when neither *base* nor
              *cwd* is provided.
        cwd: Project root from which to DISCOVER the docs base. When given, the
             resolver searches ordered candidate bases under *cwd* and prefers
             the non-default docs/nwave/feature over docs/feature.

    Returns:
        Path to the execution-log.json file.

    Raises:
        FileNotFoundError: No execution-log.json found under any candidate base.
        ValueError: Multiple execution-log.json files found within a single base
                    and deliver/ is absent — cannot determine which wave is active.
    """
    if cwd is not None and base is None:
        return _resolve_from_cwd(project_id, cwd)

    return _resolve_in_base(project_id, base if base is not None else _DEFAULT_BASE)


def _resolve_from_cwd(project_id: str, cwd: Path) -> Path:
    """Discover the docs base under *cwd*, preferring the override base."""
    last_not_found: FileNotFoundError | None = None
    for suffix in _BASE_SUFFIXES:
        try:
            return _resolve_in_base(project_id, cwd / suffix)
        except FileNotFoundError as exc:
            # Only a missing log advances to the next candidate base. A
            # ValueError (ambiguous: 2+ wave logs in this base, no deliver/)
            # propagates immediately by design — true ambiguity is unresolvable,
            # and falling through to another base would mask it.
            last_not_found = exc

    raise last_not_found or FileNotFoundError(
        f"No execution-log.json for {project_id} under any base below {cwd}."
    )


def _resolve_in_base(project_id: str, base: Path) -> Path:
    """Resolve the log within a single base directory."""
    project_dir = base / project_id

    deliver_log = project_dir / "deliver" / "execution-log.json"
    if deliver_log.exists():
        return deliver_log

    candidates = list(project_dir.glob("*/execution-log.json"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(
            f"No execution-log.json under {project_dir}. "
            "The project may not have been initialized for this wave."
        )
    raise ValueError(
        f"Ambiguous: {len(candidates)} execution-log.json files found under "
        f"{project_dir}. Cannot determine active wave. "
        f"Candidates: {[str(c) for c in sorted(candidates)]}"
    )
