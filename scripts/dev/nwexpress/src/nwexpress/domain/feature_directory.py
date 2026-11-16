"""Where a run writes its feature documents: resolved by nwdes, so both tools share one set of rules.

The keys, the tier precedence (feature over repository over global), the defaults and the refusals all belong to
nwdes (src/nwdes/destinations.py). This module only converts nwdes's results into nwexpress's Refusal and into the
four paths a run writes. A refused value is raised as a Refusal carrying nwdes's WHAT, WHY and HOW.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from nwexpress.domain.feature_id import FeatureId
from nwexpress.domain.nwdes_source import nwdes_module
from nwexpress.domain.refusal import Refusal


BRIEF_NAME = "brief.md"
ARCHITECTURE_NAME = "architecture.md"
ACCEPTANCE_NAME = "acceptance.md"
TRACE_NAME = "TRACE.md"
DOCUMENT_NAMES = (BRIEF_NAME, ARCHITECTURE_NAME, ACCEPTANCE_NAME, TRACE_NAME)


@dataclass(frozen=True)
class Destination:
    folder: str
    briefs: tuple[str, str, str]
    trace: str


def _value(result: Any) -> Any:
    """The value of a built nwdes result; a refused one becomes a Refusal with nwdes's first defect."""
    built = nwdes_module("nwdes.contracts")
    if isinstance(result, built.Refused):
        defect = result.defects[0]
        raise Refusal(what=defect.what, why=defect.why, how=defect.how)
    if not isinstance(result, built.Built):
        raise TypeError(f"unexpected nwdes result {result!r}")
    return result.value


def parse_tier(kind: str, name: str, document: Any) -> Any:
    """The nwdes result for one decoded configuration document; a refusal stays a value until resolve raises it.

    None is an absent file, which declares nothing.
    """
    destinations = nwdes_module("nwdes.destinations")
    if document is None:
        return destinations.ConfigurationTier(kind, name)
    return destinations.parse_tier(kind, name, json.dumps(document).encode("utf-8"))


def resolve(tiers: tuple[Any, ...], feature_id: str) -> Destination:
    """The folder and the document paths of one feature, from tiers nwdes read or parsed."""
    feature = FeatureId.of(feature_id)
    destinations = nwdes_module("nwdes.destinations")
    value = _value(
        destinations.resolve(
            tuple(tiers), SimpleNamespace(kind="Feature", id=feature.text)
        )
    )
    briefs = tuple(path for _, path in value.briefs)
    folder = briefs[0].rpartition("/")[0]
    return Destination(
        folder=folder,
        briefs=(briefs[0], briefs[1], briefs[2]),
        trace=f"{folder}/{TRACE_NAME}",
    )
