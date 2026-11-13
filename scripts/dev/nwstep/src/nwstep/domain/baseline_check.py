"""What a case observed on the pre-feature tree: held, differed, or could not be verified; and whether the declared cause appeared."""

from __future__ import annotations

from nwstep.domain.case_expectation import CaseExpectation
from nwstep.domain.command_outcome import CommandOutcome


class BaselineCheck:
    HELD = "held"
    DIFFERS = "differs"
    COULD_NOT_VERIFY = "could-not-verify"

    def __init__(
        self,
        status: str,
        observed: str,
        exit_code: int | None = None,
        cause: str | None = None,
        cause_seen: bool | None = None,
    ) -> None:
        self.status = status
        self.observed = observed
        self.exit_code = exit_code
        self.cause = cause
        self.cause_seen = cause_seen

    @property
    def held(self) -> bool:
        return self.status == self.HELD

    @classmethod
    def could_not_verify(cls, reason: str) -> BaselineCheck:
        return cls(cls.COULD_NOT_VERIFY, reason)

    USAGE_ERROR_EXIT = 4

    @classmethod
    def of(cls, expectation: CaseExpectation, outcome: CommandOutcome) -> BaselineCheck:
        if outcome.exit_code == cls.USAGE_ERROR_EXIT:
            return cls.could_not_verify(
                f"the command exits {cls.USAGE_ERROR_EXIT} (usage error) on the pre-feature tree: "
                "it names a path or a test that the pre-feature tree does not have"
            )
        held = expectation.holds(outcome)
        cause = expectation.baseline_contains
        return cls(
            cls.HELD if held else cls.DIFFERS,
            expectation.observed(outcome),
            outcome.exit_code,
            cause,
            None if cause is None else expectation.cause_seen(outcome),
        )

    def describe(self) -> str:
        """One line for a refusal or a brief, read after the candidate outcome."""
        if self.status == self.COULD_NOT_VERIFY:
            return f"pre-feature could not be verified: {self.observed}"
        label = "held" if self.held else "NOT HELD"
        text = f"pre-feature {label}: {self.observed}"
        if self.cause is not None:
            seen = "seen" if self.cause_seen else "NOT seen"
            text += f"; cause '{self.cause}' {seen}"
        return text

    def as_value(self) -> dict[str, object]:
        return {
            "status": self.status,
            "observed": self.observed,
            "exit_code": self.exit_code,
            "cause": self.cause,
            "cause_seen": self.cause_seen,
        }
