"""The test identities a declared verification command reports, read from its JUnit XML report.

Pure: report bytes in, outcomes out. The shell runs the declared command and reads the report;
this module decides what counts as an identity and which identities a candidate must keep.
An identity is classname::name of a JUnit testcase. Its outcome is pass, fail or skip; an
identity the report does not contain is not reported.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


PASS = "pass"
FAIL = "fail"
SKIP = "skip"


def read_report(data: bytes) -> dict[str, str] | None:
    """The outcome of each identity the report names, or None when the bytes are not XML.

    A repeated identity keeps every non-pass outcome: it passes only when each run of it passes.
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    outcomes: dict[str, str] = {}
    for case in root.iter("testcase"):
        identity = case.get("classname", "") + "::" + case.get("name", "")
        outcome = _outcome(case)
        previous = outcomes.get(identity)
        outcomes[identity] = (
            outcome if previous is None or outcome != PASS else previous
        )
    return outcomes


def _outcome(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return FAIL
    if case.find("skipped") is not None:
        return SKIP
    return PASS


def not_passing(
    approved: Mapping[str, str], observed: Mapping[str, str] | None
) -> tuple[tuple[str, str | None], ...]:
    """Each identity the approval names that the candidate does not report pass, in name order.

    The second element is the outcome the candidate reports, or None when it reports nothing.
    The approved outcome is not compared: a RED-first approval records a fail, and the candidate
    must pass; what the approval fixes is the identity.
    """
    reported = observed or {}
    return tuple(
        (identity, reported.get(identity))
        for identity in sorted(approved)
        if reported.get(identity) != PASS
    )


MUTANT_FIELDS = frozenset(("path", "old", "new", "targets"))


def read_mutants(data: bytes | None) -> tuple[dict, ...] | None:
    """The declared mutants, or None when the bytes are not a JSON list of mutant objects.

    A mutant names a file of the product, the text it replaces (old, which must occur), the text
    that replaces it (new, which may be empty) and the identities it must make fail (targets).
    """
    if data is None:
        return None
    try:
        listed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(listed, list):
        return None
    mutants = []
    for item in listed:
        if not isinstance(item, dict) or set(item) != MUTANT_FIELDS:
            return None
        if not (
            isinstance(item["path"], str)
            and item["path"]
            and isinstance(item["old"], str)
            and item["old"]
            and isinstance(item["new"], str)
        ):
            return None
        targets = item["targets"]
        if not (
            isinstance(targets, list)
            and targets
            and all(isinstance(target, str) and target for target in targets)
        ):
            return None
        mutants.append(dict(item, targets=tuple(targets)))
    return tuple(mutants)


def untargeted(
    identities: Mapping[str, str], mutants: tuple[dict, ...]
) -> tuple[str, ...]:
    """The identities no declared mutant targets, in name order."""
    targeted = {target for mutant in mutants for target in mutant["targets"]}
    return tuple(
        sorted(identity for identity in identities if identity not in targeted)
    )


def unknown_targets(
    identities: Mapping[str, str], mutants: tuple[dict, ...]
) -> tuple[str, ...]:
    """The targets that name no identity the approval reported, in name order."""
    return tuple(
        sorted(
            {
                target
                for mutant in mutants
                for target in mutant["targets"]
                if target not in identities
            }
        )
    )


def survivors(
    mutant: dict, observed: Mapping[str, str] | None
) -> tuple[tuple[str, str | None], ...]:
    """The targets of one mutant that do not fail under it, with the outcome reported (None when
    absent). A mutant kills a target only by making it fail."""
    reported = observed or {}
    return tuple(
        (target, reported.get(target))
        for target in mutant["targets"]
        if reported.get(target) != FAIL
    )
