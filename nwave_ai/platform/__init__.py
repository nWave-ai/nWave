"""The platform names the installed nwave-ai serves without the old des package.

Every module under this package imports nothing from ``des`` (architectural test T18).
The package holds copies of the closure that the installed surface still uses; the
old ``des`` definitions remain until their deletion slice.
"""

from __future__ import annotations

from nwave_ai.platform.config import effective_config
from nwave_ai.platform.regions import communication_rules_body, project_asset


__all__ = ["communication_rules_body", "effective_config", "project_asset"]
