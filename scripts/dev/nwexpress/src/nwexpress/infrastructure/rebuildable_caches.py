"""The closed list of rebuildable cache folder names, read from the data file beside this module.

The list is data, not code: the proof decides with the names it is given, and the names live in one file that a person
reads and changes. A line that is blank or starts with # is not a name.
"""

from __future__ import annotations

from pathlib import Path


DATA_FILE = Path(__file__).with_name("rebuildable_caches.txt")


def load_cache_names() -> frozenset[str]:
    return frozenset(
        line.strip()
        for line in DATA_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )
