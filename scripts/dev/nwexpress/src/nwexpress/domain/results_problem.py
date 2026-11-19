"""Why the repository's results file of a RED does not carry the RED's proof: its kind and the cause the report gives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultsProblem:
    kind: str
    cause: str
