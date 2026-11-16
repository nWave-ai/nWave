"""Reads the global, repository and feature configuration tiers with the nwdes reader.

The reader is nwdes's own (src/nwdes/shell/json_configuration.py read_configuration_tier): the global file in the
home directory, the repository file at the root and the feature file under .nwave/features/<feature id>. Missing
files declare nothing; unreadable, malformed or refused files come back as refusals that the resolver raises.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from nwexpress.domain.nwdes_source import nwdes_module


TIERS = ("global", "repository", "feature")


def read_tiers(root: Path, feature: str, home: Path) -> tuple[object, ...]:
    """The three tiers in ascending precedence, as nwdes reads them for a feature scope."""
    reader = nwdes_module("nwdes.shell.json_configuration").read_configuration_tier
    scope = SimpleNamespace(kind="Feature", id=feature)
    global_config = str(home / ".nwave" / "config.json")
    return tuple(reader(str(root), global_config, kind, scope) for kind in TIERS)
