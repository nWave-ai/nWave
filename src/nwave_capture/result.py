from dataclasses import dataclass
from typing import TypeAlias

from .contracts import _digest, _string


@dataclass(frozen=True)
class Complete:
    certificate_digest: str

    def __post_init__(self):
        _digest(self.certificate_digest)


def _failures(values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError("expected tuple")
    if not values:
        raise ValueError("tuple must be non-empty")
    for value in values:
        _string(value)


@dataclass(frozen=True)
class Incomplete:
    known_failures: tuple[str, ...]

    def __post_init__(self):
        _failures(self.known_failures)


@dataclass(frozen=True)
class Indeterminate:
    unknowns: tuple[str, ...]

    def __post_init__(self):
        _failures(self.unknowns)


CaptureResult: TypeAlias = Complete | Incomplete | Indeterminate
