"""What the machine has right now: usable cores and available memory.

Effects only, standard library only. A fact that cannot be read on this platform is
``None`` and comes with a note; ``queue_policy.concurrency`` then falls back to one
run at a time. Nothing here knows a number of any particular machine.
"""

from __future__ import annotations

import os
from pathlib import Path

from nwave_ai.testrun.queue_policy import MachineCapacity


_MEMORY_FACTS = Path("/proc/meminfo")
_AVAILABLE_LABEL = "MemAvailable:"


def _usable_cores() -> int | None:
    """The cores this process may use: its affinity where known, else the count."""
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        try:
            return len(affinity(0)) or None
        except OSError:
            pass
    return os.cpu_count()


def _available_memory_mb() -> int | None:
    """Memory available to new work, in megabytes, where the kernel publishes it."""
    try:
        lines = _MEMORY_FACTS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if line.startswith(_AVAILABLE_LABEL):
            words = line.split()
            if len(words) >= 2 and words[1].isdigit():
                return int(words[1]) // 1024
    return None


def read_machine() -> tuple[MachineCapacity, tuple[str, ...]]:
    """The machine facts and a note for each one that could not be read."""
    cores, memory = _usable_cores(), _available_memory_mb()
    notes = tuple(
        f"NOTE: {fact} cannot be read on this platform; one run at a time, "
        "the declared fallback, applies whatever the ceiling"
        for fact, value in (
            ("the number of cores", cores),
            ("available memory", memory),
        )
        if value is None
    )
    return MachineCapacity(cores, memory), notes
