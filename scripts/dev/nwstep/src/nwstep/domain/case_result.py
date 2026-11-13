"""The observed result of one case and the rule that accepts or refuses it, decided by the case's kind."""

from __future__ import annotations

from dataclasses import dataclass

from nwstep.domain.baseline_check import BaselineCheck
from nwstep.domain.case_expectation import CaseExpectation
from nwstep.domain.protection_check import ProtectionCheck


@dataclass(frozen=True)
class CaseResult:
    identifier: str
    argv: tuple[str, ...]
    expectation: str
    kind: str
    held: bool
    observed: str
    exit_code: int | None
    output_tail: tuple[str, ...]
    baseline: BaselineCheck
    protection: ProtectionCheck

    TAIL_LINES = 20

    def refusal(self) -> str | None:
        """Why the differential does not prove this case; None when it does or cannot be checked here."""
        if self.kind == CaseExpectation.NEW:
            return self._new_refusal()
        return self._preserve_refusal()

    def _new_refusal(self) -> str | None:
        if self.baseline.status == BaselineCheck.COULD_NOT_VERIFY:
            return None
        if self.baseline.held:
            return f"'{self.identifier}' holds on the pre-feature tree too, so it cannot show the change"
        if not self.baseline.cause_seen:
            return f"on the pre-feature tree it fails, but its output lacks the declared cause '{self.baseline.cause}'"
        return None

    def _preserve_refusal(self) -> str | None:
        if self.baseline.status == BaselineCheck.COULD_NOT_VERIFY:
            return None
        if not self.baseline.held:
            return f"'{self.identifier}' does not hold on the pre-feature tree, so it does not preserve the behaviour"
        path = self.protection.path
        if self.protection.status == ProtectionCheck.NOT_CHANGED:
            return f"'{path}' is not among the files changed from BASE to HEAD"
        if self.protection.status == ProtectionCheck.NOT_EXECUTED:
            return f"no line of '{path}' ran in the candidate run"
        return None

    def unverified_reason(self) -> str | None:
        """Why this case could not be checked against the pre-feature tree or its trace, if it could not."""
        if self.baseline.status == BaselineCheck.COULD_NOT_VERIFY:
            return self.baseline.observed
        if self.protection.status == ProtectionCheck.COULD_NOT_VERIFY:
            return self.protection.detail
        return None

    def differential_text(self) -> str:
        parts = [self.baseline.describe(), self.protection.describe()]
        return "; ".join(part for part in parts if part)

    def as_value(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "argv": list(self.argv),
            "expect": self.expectation,
            "kind": self.kind,
            "held": self.held,
            "observed": self.observed,
            "exit_code": self.exit_code,
            "output_tail": list(self.output_tail),
            "baseline": self.baseline.as_value(),
            "protection": self.protection.as_value(),
            "differential": self.differential_text(),
        }
