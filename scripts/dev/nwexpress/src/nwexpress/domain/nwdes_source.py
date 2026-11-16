"""Loads nwdes modules from the repository that ships this nwexpress, only when a feature command needs them.

nwdes is the one owner of the feature folder rules (src/nwdes/destinations.py, src/nwdes/handoff.py). nwexpress reaches
them the way it already reaches nwave_ai (infrastructure/command_runner.py): from the repository's src directory.
The import is lazy, so every other nwexpress command runs without nwdes present; a feature command that cannot import
it is refused with WHAT, WHY and HOW rather than failing at start-up.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

from nwexpress.domain.refusal import Refusal


REPOSITORY_SOURCE = Path(__file__).resolve().parents[6] / "src"


def nwdes_module(name: str) -> ModuleType:
    """The named nwdes module, imported from the repository source; a Refusal when it cannot be imported."""
    if str(REPOSITORY_SOURCE) not in sys.path:
        sys.path.insert(0, str(REPOSITORY_SOURCE))
    try:
        return importlib.import_module(name)
    except ImportError as error:
        raise Refusal(
            what=f"the nwdes module {name} cannot be imported: {error}",
            why="the feature folder rules belong to nwdes, and nwexpress reads them from the repository source it ships with",
            how=f"run nwexpress from the repository that ships nwdes, so that {REPOSITORY_SOURCE} holds the nwdes package",
        ) from None
