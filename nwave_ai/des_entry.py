"""Console-script shims for the des-* entry points.

The DES runtime ships inside the wheel as installer payload at
``nWave/lib/python/des`` (with imports rewritten to top-level ``des``), not
as an importable site-packages package. Entry points that target
``des.cli.*`` directly therefore crash with ``ModuleNotFoundError`` in any
installed environment (pip/pipx/uv tool).

These wrappers locate the payload — preferring the version-matched copy
shipped next to this package, falling back to the nWave installer target at
``~/.claude/lib/python`` — prepend it to ``sys.path``, and dispatch to the
real ``des.cli.*`` main. This mirrors what the ``nWave/scripts/des/*`` shims
do, but through the standard console-script mechanism so the PATH-visible
commands actually work.
"""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path


def _payload_candidates() -> tuple[Path, ...]:
    return (
        # site-packages/nWave/lib/python — shipped in this wheel, version-matched
        Path(__file__).resolve().parent.parent / "nWave" / "lib" / "python",
        # nWave installer target (`nwave-ai install`)
        Path.home() / ".claude" / "lib" / "python",
    )


def _locate_payload() -> Path | None:
    for candidate in _payload_candidates():
        if (candidate / "des" / "__init__.py").is_file():
            return candidate
    return None


def _dispatch(module_name: str) -> int:
    payload = _locate_payload()
    if payload is None:
        searched = ", ".join(str(c) for c in _payload_candidates())
        sys.stderr.write(f"ERROR: DES runtime not found (searched: {searched})\n")
        return 1
    payload_str = str(payload)
    if payload_str not in sys.path:
        sys.path.insert(0, payload_str)
    result = import_module(module_name).main()
    return 0 if result is None else int(result)


def log_phase() -> None:
    raise SystemExit(_dispatch("des.cli.log_phase"))


def commit() -> None:
    raise SystemExit(_dispatch("des.cli.commit"))


def init_log() -> None:
    raise SystemExit(_dispatch("des.cli.init_log"))


def verify_integrity() -> None:
    raise SystemExit(_dispatch("des.cli.verify_deliver_integrity"))


def roadmap() -> None:
    raise SystemExit(_dispatch("des.cli.roadmap"))


def health_check() -> None:
    raise SystemExit(_dispatch("des.cli.health_check"))
